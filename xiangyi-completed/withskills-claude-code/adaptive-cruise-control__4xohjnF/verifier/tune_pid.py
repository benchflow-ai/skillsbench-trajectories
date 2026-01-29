"""PID parameter tuning for ACC system."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_gains, distance_gains, config, sensor_df, dt):
    """Run simulation with given PID parameters.

    Args:
        speed_gains: Dict with kp, ki, kd for speed controller
        distance_gains: Dict with kp, ki, kd for distance controller
        config: Base configuration dict
        sensor_df: Sensor data DataFrame
        dt: Time step

    Returns:
        dict: Performance metrics
    """
    # Update config with new gains
    config['pid_speed'] = speed_gains
    config['pid_distance'] = distance_gains

    # Create ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize simulation
    ego_speed = 0.0
    speeds = []
    distance_errors = []
    modes = []
    min_distance = float('inf')

    # Run simulation
    for i, row in sensor_df.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed (simple Euler integration)
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        speeds.append(ego_speed)
        distance_errors.append(dist_error)
        modes.append(mode)

        if distance is not None:
            min_distance = min(min_distance, distance)

    speeds = np.array(speeds)

    # Calculate metrics
    metrics = {}

    # Speed rise time (time to reach 90% of set speed in cruise mode)
    target_speed = config['acc_settings']['set_speed']
    rise_threshold = 0.9 * target_speed
    rise_indices = np.where(speeds >= rise_threshold)[0]
    if len(rise_indices) > 0:
        metrics['rise_time'] = rise_indices[0] * dt
    else:
        metrics['rise_time'] = float('inf')

    # Speed overshoot (during initial cruise phase, before lead vehicle appears)
    cruise_phase_end = 300  # First 30 seconds
    cruise_speeds = speeds[:cruise_phase_end]
    max_speed = np.max(cruise_speeds)
    metrics['overshoot_percent'] = max(0, (max_speed - target_speed) / target_speed * 100)

    # Steady-state error for speed (last 5 seconds of cruise mode before lead vehicle)
    cruise_steady_start = 250  # 25 seconds
    cruise_steady_end = 300  # 30 seconds
    steady_speeds = speeds[cruise_steady_start:cruise_steady_end]
    metrics['speed_ss_error'] = np.abs(np.mean(steady_speeds) - target_speed)

    # Distance steady-state error (when following)
    follow_errors = [e for e, m in zip(distance_errors, modes) if m == 'follow' and e is not None]
    if follow_errors:
        # Take last 20% of following period for steady state
        steady_follow = follow_errors[int(len(follow_errors)*0.8):]
        metrics['distance_ss_error'] = np.abs(np.mean(steady_follow))
    else:
        metrics['distance_ss_error'] = 0.0

    # Minimum distance
    metrics['min_distance'] = min_distance if min_distance != float('inf') else float('nan')

    # Combined score (lower is better)
    # Penalize if constraints are violated
    score = 0.0

    if metrics['rise_time'] > 10.0:
        score += (metrics['rise_time'] - 10.0) * 10  # Heavy penalty

    if metrics['overshoot_percent'] > 5.0:
        score += (metrics['overshoot_percent'] - 5.0) * 5

    score += metrics['speed_ss_error'] * 20

    if not np.isnan(metrics['distance_ss_error']):
        score += metrics['distance_ss_error'] * 10

    if not np.isnan(metrics['min_distance']) and metrics['min_distance'] < 5.0:
        score += (5.0 - metrics['min_distance']) * 50  # Heavy penalty

    metrics['score'] = score

    return metrics


def tune_pid():
    """Tune PID parameters using grid search."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_df = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']

    print("Starting PID tuning...")
    print("=" * 60)

    # Grid search for speed controller (cruise mode is critical)
    best_score = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None

    # Speed controller: Need strong response for rise time < 10s
    speed_kp_range = [0.5, 1.0, 1.5, 2.0, 2.5]
    speed_ki_range = [0.05, 0.1, 0.15, 0.2]
    speed_kd_range = [0.0, 0.5, 1.0, 1.5]

    # Distance controller: Need smooth following
    dist_kp_range = [0.3, 0.5, 0.8, 1.0]
    dist_ki_range = [0.01, 0.05, 0.1]
    dist_kd_range = [0.5, 1.0, 1.5, 2.0]

    total_iterations = len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) * \
                      len(dist_kp_range) * len(dist_ki_range) * len(dist_kd_range)

    iteration = 0

    for s_kp in speed_kp_range:
        for s_ki in speed_ki_range:
            for s_kd in speed_kd_range:
                speed_gains = {'kp': s_kp, 'ki': s_ki, 'kd': s_kd}

                for d_kp in dist_kp_range:
                    for d_ki in dist_ki_range:
                        for d_kd in dist_kd_range:
                            iteration += 1
                            distance_gains = {'kp': d_kp, 'ki': d_ki, 'kd': d_kd}

                            try:
                                metrics = simulate_with_params(
                                    speed_gains, distance_gains, config.copy(), sensor_df, dt
                                )

                                if metrics['score'] < best_score:
                                    best_score = metrics['score']
                                    best_speed_gains = speed_gains.copy()
                                    best_distance_gains = distance_gains.copy()
                                    best_metrics = metrics.copy()

                                    print(f"\nIteration {iteration}/{total_iterations}")
                                    print(f"New best score: {best_score:.2f}")
                                    print(f"Speed PID: Kp={s_kp}, Ki={s_ki}, Kd={s_kd}")
                                    print(f"Distance PID: Kp={d_kp}, Ki={d_ki}, Kd={d_kd}")
                                    print(f"  Rise time: {metrics['rise_time']:.2f}s")
                                    print(f"  Overshoot: {metrics['overshoot_percent']:.2f}%")
                                    print(f"  Speed SS error: {metrics['speed_ss_error']:.3f} m/s")
                                    print(f"  Distance SS error: {metrics['distance_ss_error']:.3f} m")
                                    print(f"  Min distance: {metrics['min_distance']:.2f} m")

                            except Exception as e:
                                print(f"Error with params: {e}")
                                continue

                            if iteration % 100 == 0:
                                print(f"Progress: {iteration}/{total_iterations} ({100*iteration/total_iterations:.1f}%)")

    print("\n" + "=" * 60)
    print("TUNING COMPLETE")
    print("=" * 60)
    print(f"\nBest Speed PID gains:")
    print(f"  Kp: {best_speed_gains['kp']}")
    print(f"  Ki: {best_speed_gains['ki']}")
    print(f"  Kd: {best_speed_gains['kd']}")
    print(f"\nBest Distance PID gains:")
    print(f"  Kp: {best_distance_gains['kp']}")
    print(f"  Ki: {best_distance_gains['ki']}")
    print(f"  Kd: {best_distance_gains['kd']}")
    print(f"\nPerformance metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot_percent']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance SS error: {best_metrics['distance_ss_error']:.3f} m (target: <2m)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m)")

    # Save results
    results = {
        'pid_speed': {
            'kp': float(best_speed_gains['kp']),
            'ki': float(best_speed_gains['ki']),
            'kd': float(best_speed_gains['kd'])
        },
        'pid_distance': {
            'kp': float(best_distance_gains['kp']),
            'ki': float(best_distance_gains['ki']),
            'kd': float(best_distance_gains['kd'])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)

    print(f"\nResults saved to tuning_results.yaml")

    return results


if __name__ == '__main__':
    tune_pid()

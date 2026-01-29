"""Refined PID parameter tuning for ACC system."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_gains, distance_gains, config, sensor_df, dt):
    """Run simulation with given PID parameters."""
    # Update config with new gains
    config['pid_speed'] = speed_gains
    config['pid_distance'] = distance_gains

    # Create ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize simulation
    ego_speed = 0.0
    speeds = []
    distance_errors = []
    distances_actual = []
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
        distances_actual.append(distance)
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

    # Distance steady-state error (when following, excluding emergency)
    follow_indices = [i for i, m in enumerate(modes) if m == 'follow']
    if follow_indices:
        # Calculate desired distance for each follow point
        follow_dist_errors = []
        for idx in follow_indices:
            if distances_actual[idx] is not None and distance_errors[idx] is not None:
                follow_dist_errors.append(abs(distance_errors[idx]))

        if follow_dist_errors:
            # Take last 30% of following period for steady state
            steady_follow = follow_dist_errors[int(len(follow_dist_errors)*0.7):]
            if steady_follow:
                metrics['distance_ss_error'] = np.mean(steady_follow)
            else:
                metrics['distance_ss_error'] = 0.0
        else:
            metrics['distance_ss_error'] = 0.0
    else:
        metrics['distance_ss_error'] = 0.0

    # Minimum distance
    metrics['min_distance'] = min_distance if min_distance != float('inf') else float('nan')

    # Combined score (lower is better, heavily weighted toward meeting constraints)
    score = 0.0

    # Rise time penalty (must be < 10s)
    if metrics['rise_time'] > 10.0:
        score += (metrics['rise_time'] - 10.0) ** 2 * 100
    else:
        score += metrics['rise_time'] * 2  # Reward faster rise time

    # Overshoot penalty (must be < 5%)
    if metrics['overshoot_percent'] > 5.0:
        score += (metrics['overshoot_percent'] - 5.0) ** 2 * 10
    else:
        score += metrics['overshoot_percent'] * 0.5

    # Speed steady-state error penalty (must be < 0.5 m/s)
    if metrics['speed_ss_error'] > 0.5:
        score += (metrics['speed_ss_error'] - 0.5) ** 2 * 100
    else:
        score += metrics['speed_ss_error'] * 5

    # Distance steady-state error penalty (must be < 2m)
    if metrics['distance_ss_error'] > 2.0:
        score += (metrics['distance_ss_error'] - 2.0) ** 2 * 50
    else:
        score += metrics['distance_ss_error'] * 2

    # Minimum distance penalty (must be > 5m) - CRITICAL SAFETY
    if not np.isnan(metrics['min_distance']) and metrics['min_distance'] < 5.0:
        score += (5.0 - metrics['min_distance']) ** 2 * 500

    metrics['score'] = score
    return metrics


def tune_pid_refined():
    """Refined PID tuning with better parameter ranges."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_df = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']

    print("Starting refined PID tuning...")
    print("=" * 60)

    best_score = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None

    # Refined ranges based on control theory
    # Speed controller: Need P for responsiveness, I for SS error, D for damping
    speed_kp_range = [1.0, 1.5, 2.0, 2.5, 3.0]
    speed_ki_range = [0.1, 0.2, 0.3, 0.4]
    speed_kd_range = [2.0, 3.0, 4.0]

    # Distance controller: Need moderate P, low I, high D for smooth following
    dist_kp_range = [0.5, 0.8, 1.0, 1.2]
    dist_ki_range = [0.0, 0.02, 0.05]
    dist_kd_range = [2.0, 3.0, 4.0]

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

                                    # Check if all constraints are met
                                    meets_constraints = (
                                        metrics['rise_time'] < 10.0 and
                                        metrics['overshoot_percent'] < 5.0 and
                                        metrics['speed_ss_error'] < 0.5 and
                                        metrics['distance_ss_error'] < 2.0 and
                                        (np.isnan(metrics['min_distance']) or metrics['min_distance'] > 5.0)
                                    )

                                    print(f"\nIteration {iteration}/{total_iterations}")
                                    print(f"New best score: {best_score:.2f} {'✓ MEETS ALL CONSTRAINTS' if meets_constraints else ''}")
                                    print(f"Speed PID: Kp={s_kp}, Ki={s_ki}, Kd={s_kd}")
                                    print(f"Distance PID: Kp={d_kp}, Ki={d_ki}, Kd={d_kd}")
                                    print(f"  Rise time: {metrics['rise_time']:.2f}s {'✓' if metrics['rise_time'] < 10.0 else '✗'}")
                                    print(f"  Overshoot: {metrics['overshoot_percent']:.2f}% {'✓' if metrics['overshoot_percent'] < 5.0 else '✗'}")
                                    print(f"  Speed SS error: {metrics['speed_ss_error']:.3f} m/s {'✓' if metrics['speed_ss_error'] < 0.5 else '✗'}")
                                    print(f"  Distance SS error: {metrics['distance_ss_error']:.3f} m {'✓' if metrics['distance_ss_error'] < 2.0 else '✗'}")
                                    print(f"  Min distance: {metrics['min_distance']:.2f} m {'✓' if (np.isnan(metrics['min_distance']) or metrics['min_distance'] > 5.0) else '✗'}")

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
    tune_pid_refined()

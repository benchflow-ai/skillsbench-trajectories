"""PID tuning script for ACC system."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_gains, distance_gains, sensor_data, config, dt):
    """Run simulation with given PID parameters.

    Args:
        speed_gains: (kp, ki, kd) for speed controller
        distance_gains: (kp, ki, kd) for distance controller
        sensor_data: DataFrame with sensor data
        config: Configuration dictionary
        dt: Time step

    Returns:
        Dictionary with performance metrics
    """
    # Update config with new gains
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    speeds = []
    times = []
    min_distance = float('inf')
    distance_errors = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed = max(0, ego_speed + acceleration_cmd * dt)

        speeds.append(ego_speed)
        times.append(row['time'])

        if distance is not None:
            min_distance = min(min_distance, distance)
            if distance_error is not None:
                distance_errors.append(abs(distance_error))

    speeds = np.array(speeds)
    times = np.array(times)

    # Calculate metrics for cruise phase (before lead vehicle appears)
    cruise_mask = times < 30.0
    cruise_speeds = speeds[cruise_mask]
    cruise_times = times[cruise_mask]

    # Rise time (time to reach 90% of set speed)
    set_speed = config['acc_settings']['set_speed']
    target_90 = 0.9 * set_speed
    rise_time_idx = np.where(cruise_speeds >= target_90)[0]
    rise_time = cruise_times[rise_time_idx[0]] if len(rise_time_idx) > 0 else float('inf')

    # Overshoot
    max_speed = np.max(cruise_speeds)
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error (last 5 seconds of cruise)
    steady_state_mask = (times >= 25.0) & (times < 30.0)
    if np.any(steady_state_mask):
        steady_state_error = np.abs(np.mean(speeds[steady_state_mask]) - set_speed)
    else:
        steady_state_error = float('inf')

    # Distance steady-state error
    if len(distance_errors) > 0:
        distance_ss_error = np.mean(distance_errors[-50:]) if len(distance_errors) >= 50 else np.mean(distance_errors)
    else:
        distance_ss_error = 0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'steady_state_error': steady_state_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance
    }


def evaluate_params(speed_gains, distance_gains, sensor_data, config, dt):
    """Evaluate PID parameters against requirements.

    Returns:
        Score (lower is better), metrics dictionary
    """
    metrics = simulate_with_params(speed_gains, distance_gains, sensor_data, config, dt)

    # Penalty for violating constraints
    penalty = 0
    if metrics['rise_time'] > 10:
        penalty += (metrics['rise_time'] - 10) * 10
    if metrics['overshoot'] > 5:
        penalty += (metrics['overshoot'] - 5) * 10
    if metrics['steady_state_error'] > 0.5:
        penalty += (metrics['steady_state_error'] - 0.5) * 20
    if metrics['distance_ss_error'] > 2:
        penalty += (metrics['distance_ss_error'] - 2) * 10
    if metrics['min_distance'] < 5:
        penalty += (5 - metrics['min_distance']) * 50

    # Objective: minimize rise time and errors
    score = metrics['rise_time'] + metrics['steady_state_error'] * 5 + metrics['distance_ss_error'] * 2 + penalty

    return score, metrics


def grid_search(sensor_data, config, dt):
    """Perform grid search for optimal PID gains."""
    # Speed controller gains (more aggressive for fast rise time)
    speed_kp_range = [0.5, 1.0, 1.5, 2.0, 2.5]
    speed_ki_range = [0.05, 0.1, 0.2, 0.3]
    speed_kd_range = [0.0, 0.1, 0.2, 0.5]

    # Distance controller gains (smoother for comfortable following)
    dist_kp_range = [0.3, 0.5, 0.8, 1.0]
    dist_ki_range = [0.01, 0.05, 0.1]
    dist_kd_range = [0.1, 0.3, 0.5, 1.0]

    best_score = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None

    print("Starting PID tuning...")
    total_iterations = len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) * \
                       len(dist_kp_range) * len(dist_ki_range) * len(dist_kd_range)
    iteration = 0

    for speed_kp in speed_kp_range:
        for speed_ki in speed_ki_range:
            for speed_kd in speed_kd_range:
                for dist_kp in dist_kp_range:
                    for dist_ki in dist_ki_range:
                        for dist_kd in dist_kd_range:
                            iteration += 1
                            if iteration % 100 == 0:
                                print(f"Progress: {iteration}/{total_iterations}")

                            speed_gains = (speed_kp, speed_ki, speed_kd)
                            distance_gains = (dist_kp, dist_ki, dist_kd)

                            score, metrics = evaluate_params(speed_gains, distance_gains, sensor_data, config, dt)

                            if score < best_score:
                                best_score = score
                                best_speed_gains = speed_gains
                                best_distance_gains = distance_gains
                                best_metrics = metrics
                                print(f"\nNew best score: {score:.2f}")
                                print(f"  Speed gains: kp={speed_kp}, ki={speed_ki}, kd={speed_kd}")
                                print(f"  Distance gains: kp={dist_kp}, ki={dist_ki}, kd={dist_kd}")
                                print(f"  Metrics: {metrics}\n")

    return best_speed_gains, best_distance_gains, best_metrics


def main():
    """Main tuning function."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    dt = config['simulation']['dt']

    # Perform grid search
    best_speed_gains, best_distance_gains, best_metrics = grid_search(sensor_data, config, dt)

    print("\n" + "="*60)
    print("FINAL TUNING RESULTS")
    print("="*60)
    print(f"Speed PID: kp={best_speed_gains[0]}, ki={best_speed_gains[1]}, kd={best_speed_gains[2]}")
    print(f"Distance PID: kp={best_distance_gains[0]}, ki={best_distance_gains[1]}, kd={best_distance_gains[2]}")
    print(f"\nPerformance metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target: <5%)")
    print(f"  Speed steady-state error: {best_metrics['steady_state_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance steady-state error: {best_metrics['distance_ss_error']:.2f} m (target: <2m)")
    print(f"  Minimum distance: {best_metrics['min_distance']:.2f} m (target: >5m)")

    # Save results
    tuning_results = {
        'pid_speed': {
            'kp': float(best_speed_gains[0]),
            'ki': float(best_speed_gains[1]),
            'kd': float(best_speed_gains[2])
        },
        'pid_distance': {
            'kp': float(best_distance_gains[0]),
            'ki': float(best_distance_gains[1]),
            'kd': float(best_distance_gains[2])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

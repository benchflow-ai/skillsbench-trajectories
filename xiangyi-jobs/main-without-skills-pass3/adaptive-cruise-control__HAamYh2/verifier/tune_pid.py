"""PID Parameter Tuning Script for ACC System"""

import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl
from pid_controller import PIDController


def simulate_with_params(speed_gains, distance_gains, config, sensor_data):
    """
    Run simulation with given PID parameters.

    Returns performance metrics.
    """
    # Update config with new gains
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    ego_speed = 0.0
    speeds = []
    distance_errors = []
    min_distance_recorded = float('inf')

    # Track rise time metrics
    rise_time = None
    rise_speed_90 = 0.9 * set_speed
    max_speed = 0.0

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        speeds.append(ego_speed)

        # Track metrics
        if mode == 'follow' and dist_error is not None:
            distance_errors.append(abs(dist_error))
            if distance is not None:
                min_distance_recorded = min(min_distance_recorded, distance)

        # Track rise time (time to reach 90% of set speed in cruise mode)
        if rise_time is None and ego_speed >= rise_speed_90 and lead_speed is None:
            rise_time = row['time']

        max_speed = max(max_speed, ego_speed)

    # Calculate metrics
    speeds = np.array(speeds)

    # Speed overshoot (during cruise phase before lead vehicle appears)
    cruise_speeds = speeds[:300]  # First 30 seconds
    overshoot = max(0, (cruise_speeds.max() - set_speed) / set_speed * 100)

    # Steady-state error (last 10% of cruise phase)
    cruise_steady = cruise_speeds[-30:]
    speed_ss_error = abs(cruise_steady.mean() - set_speed)

    # Distance steady-state error (when following)
    if distance_errors:
        dist_ss_error = np.mean(distance_errors[-100:]) if len(distance_errors) > 100 else np.mean(distance_errors)
    else:
        dist_ss_error = 0.0

    # Rise time
    if rise_time is None:
        rise_time = 30.0  # Penalize if not reached

    metrics = {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance_recorded
    }

    return metrics


def evaluate_performance(metrics):
    """
    Calculate overall performance score.
    Lower is better.
    """
    score = 0.0

    # Rise time penalty (target < 10s)
    if metrics['rise_time'] > 10.0:
        score += (metrics['rise_time'] - 10.0) * 10

    # Overshoot penalty (target < 5%)
    if metrics['overshoot'] > 5.0:
        score += (metrics['overshoot'] - 5.0) * 20

    # Speed steady-state error penalty (target < 0.5 m/s)
    if metrics['speed_ss_error'] > 0.5:
        score += (metrics['speed_ss_error'] - 0.5) * 50

    # Distance steady-state error penalty (target < 2m)
    if metrics['dist_ss_error'] > 2.0:
        score += (metrics['dist_ss_error'] - 2.0) * 30

    # Minimum distance penalty (must be > 5m)
    if metrics['min_distance'] < 5.0:
        score += (5.0 - metrics['min_distance']) * 100

    # Add base penalties for being close to targets
    score += metrics['rise_time']
    score += metrics['overshoot'] * 2
    score += metrics['speed_ss_error'] * 10
    score += metrics['dist_ss_error'] * 5

    return score


def grid_search_tuning():
    """Perform grid search to find optimal PID parameters."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    print("Starting PID parameter tuning...")
    print("=" * 60)

    # Grid search ranges
    speed_kp_range = [0.5, 1.0, 1.5, 2.0, 2.5]
    speed_ki_range = [0.0, 0.05, 0.1, 0.2]
    speed_kd_range = [0.0, 0.1, 0.2, 0.5]

    distance_kp_range = [0.3, 0.5, 0.8, 1.0, 1.5]
    distance_ki_range = [0.0, 0.01, 0.05, 0.1]
    distance_kd_range = [0.0, 0.2, 0.5, 1.0]

    best_score = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None

    # First, tune speed controller (cruise mode)
    print("\nPhase 1: Tuning speed controller...")
    distance_gains = [0.5, 0.01, 0.2]  # Initial guess

    for kp in speed_kp_range:
        for ki in speed_ki_range:
            for kd in speed_kd_range:
                speed_gains = [kp, ki, kd]
                metrics = simulate_with_params(speed_gains, distance_gains, config.copy(), sensor_data)
                score = evaluate_performance(metrics)

                if score < best_score:
                    best_score = score
                    best_speed_gains = speed_gains
                    best_metrics = metrics
                    print(f"  New best - Speed PID: {speed_gains}, Score: {score:.2f}, Rise time: {metrics['rise_time']:.2f}s")

    print(f"\nBest speed controller: kp={best_speed_gains[0]}, ki={best_speed_gains[1]}, kd={best_speed_gains[2]}")

    # Then, tune distance controller (follow mode)
    print("\nPhase 2: Tuning distance controller...")
    speed_gains = best_speed_gains

    for kp in distance_kp_range:
        for ki in distance_ki_range:
            for kd in distance_kd_range:
                distance_gains = [kp, ki, kd]
                metrics = simulate_with_params(speed_gains, distance_gains, config.copy(), sensor_data)
                score = evaluate_performance(metrics)

                if score < best_score:
                    best_score = score
                    best_distance_gains = distance_gains
                    best_metrics = metrics
                    print(f"  New best - Distance PID: {distance_gains}, Score: {score:.2f}, Dist error: {metrics['dist_ss_error']:.2f}m")

    print("\n" + "=" * 60)
    print("Tuning complete!")
    print(f"\nBest Speed PID gains: kp={best_speed_gains[0]}, ki={best_speed_gains[1]}, kd={best_speed_gains[2]}")
    print(f"Best Distance PID gains: kp={best_distance_gains[0]}, ki={best_distance_gains[1]}, kd={best_distance_gains[2]}")
    print(f"\nPerformance metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target < 10s)")
    print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target < 5%)")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.2f} m/s (target < 0.5 m/s)")
    print(f"  Distance SS error: {best_metrics['dist_ss_error']:.2f}m (target < 2m)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f}m (target > 5m)")

    # Save results
    results = {
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
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)

    print("\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    grid_search_tuning()

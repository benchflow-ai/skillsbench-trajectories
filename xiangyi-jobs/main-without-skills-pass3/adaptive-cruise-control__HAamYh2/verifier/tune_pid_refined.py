"""Refined PID Parameter Tuning Script for ACC System"""

import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_gains, distance_gains, config, sensor_data):
    """Run simulation with given PID parameters."""
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    ego_speed = 0.0
    speeds = []
    distance_errors = []
    min_distance_recorded = float('inf')
    rise_time = None
    rise_speed_90 = 0.9 * set_speed

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        speeds.append(ego_speed)

        if mode == 'follow' and dist_error is not None:
            distance_errors.append(abs(dist_error))
            if distance is not None:
                min_distance_recorded = min(min_distance_recorded, distance)

        if rise_time is None and ego_speed >= rise_speed_90 and lead_speed is None:
            rise_time = row['time']

    speeds = np.array(speeds)
    cruise_speeds = speeds[:300]
    overshoot = max(0, (cruise_speeds.max() - set_speed) / set_speed * 100)
    cruise_steady = cruise_speeds[-30:]
    speed_ss_error = abs(cruise_steady.mean() - set_speed)

    if distance_errors:
        dist_ss_error = np.mean(distance_errors[-100:]) if len(distance_errors) > 100 else np.mean(distance_errors)
    else:
        dist_ss_error = 0.0

    if rise_time is None:
        rise_time = 30.0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance_recorded
    }


def evaluate_performance(metrics):
    """Calculate performance score (lower is better)."""
    score = 0.0

    # Penalties for exceeding targets
    if metrics['rise_time'] > 10.0:
        score += (metrics['rise_time'] - 10.0) * 20
    if metrics['overshoot'] > 5.0:
        score += (metrics['overshoot'] - 5.0) * 30
    if metrics['speed_ss_error'] > 0.5:
        score += (metrics['speed_ss_error'] - 0.5) * 100
    if metrics['dist_ss_error'] > 2.0:
        score += (metrics['dist_ss_error'] - 2.0) * 50
    if metrics['min_distance'] < 5.0:
        score += (5.0 - metrics['min_distance']) * 200

    # Base costs
    score += metrics['rise_time'] * 0.5
    score += metrics['overshoot'] * 2
    score += metrics['speed_ss_error'] * 10
    score += metrics['dist_ss_error'] * 10

    return score


def refined_tuning():
    """Perform refined grid search with better parameter ranges."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    sensor_data = pd.read_csv('sensor_data.csv')

    print("Starting refined PID parameter tuning...")
    print("=" * 60)

    # Refined ranges based on first pass
    speed_kp_range = [1.5, 2.0, 2.5, 3.0]
    speed_ki_range = [0.0, 0.01, 0.02, 0.05]
    speed_kd_range = [0.0, 0.05, 0.1]

    distance_kp_range = [0.5, 0.8, 1.0, 1.5, 2.0, 2.5]
    distance_ki_range = [0.0, 0.01, 0.02, 0.05, 0.1]
    distance_kd_range = [0.0, 0.1, 0.3, 0.5, 1.0, 1.5]

    best_score = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None

    # Tune speed controller
    print("\nPhase 1: Tuning speed controller...")
    distance_gains = [1.0, 0.01, 0.5]

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
                    print(f"  Speed PID: [{kp:.2f}, {ki:.2f}, {kd:.2f}] - Score: {score:.2f}, Rise: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot']:.2f}%")

    print(f"\nBest speed: kp={best_speed_gains[0]}, ki={best_speed_gains[1]}, kd={best_speed_gains[2]}")

    # Tune distance controller
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
                    print(f"  Distance PID: [{kp:.2f}, {ki:.2f}, {kd:.2f}] - Score: {score:.2f}, Dist error: {metrics['dist_ss_error']:.2f}m, Min dist: {metrics['min_distance']:.2f}m")

    print("\n" + "=" * 60)
    print("Tuning complete!")
    print(f"\nOptimal Speed PID: kp={best_speed_gains[0]}, ki={best_speed_gains[1]}, kd={best_speed_gains[2]}")
    print(f"Optimal Distance PID: kp={best_distance_gains[0]}, ki={best_distance_gains[1]}, kd={best_distance_gains[2]}")
    print(f"\nFinal Performance:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target < 10s) {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target < 5%) {'✓' if best_metrics['overshoot'] < 5 else '✗'}")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.3f} m/s (target < 0.5 m/s) {'✓' if best_metrics['speed_ss_error'] < 0.5 else '✗'}")
    print(f"  Distance SS error: {best_metrics['dist_ss_error']:.2f}m (target < 2m) {'✓' if best_metrics['dist_ss_error'] < 2 else '✗'}")
    print(f"  Min distance: {best_metrics['min_distance']:.2f}m (target > 5m) {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

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
    refined_tuning()

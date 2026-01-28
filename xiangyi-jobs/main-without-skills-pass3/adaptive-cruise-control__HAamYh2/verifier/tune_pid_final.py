"""Final PID Parameter Tuning with Focus on Distance Control"""

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
    follow_mode_started = False

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        speeds.append(ego_speed)

        if mode == 'follow':
            if not follow_mode_started:
                follow_mode_started = True
                follow_start_idx = idx
            if dist_error is not None:
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

    # Calculate steady-state distance error (last 50% of following phase)
    if distance_errors:
        n_steady = len(distance_errors) // 2
        dist_ss_error = np.mean(distance_errors[-n_steady:]) if n_steady > 0 else np.mean(distance_errors)
    else:
        dist_ss_error = 0.0

    if rise_time is None:
        rise_time = 30.0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance_recorded,
        'avg_dist_error': np.mean(distance_errors) if distance_errors else 0.0
    }


def evaluate_performance(metrics):
    """Calculate performance score (lower is better)."""
    score = 0.0

    # Hard penalties for violating requirements
    if metrics['rise_time'] > 10.0:
        score += (metrics['rise_time'] - 10.0) * 50
    if metrics['overshoot'] > 5.0:
        score += (metrics['overshoot'] - 5.0) * 50
    if metrics['speed_ss_error'] > 0.5:
        score += (metrics['speed_ss_error'] - 0.5) * 200
    if metrics['dist_ss_error'] > 2.0:
        score += (metrics['dist_ss_error'] - 2.0) * 100  # High penalty
    if metrics['min_distance'] < 5.0:
        score += (5.0 - metrics['min_distance']) * 500

    # Base costs for optimization
    score += metrics['rise_time'] * 0.5
    score += metrics['overshoot']
    score += metrics['speed_ss_error'] * 5
    score += metrics['dist_ss_error'] * 20  # Prioritize distance error

    return score


def final_tuning():
    """Perform final tuning with very high distance controller gains."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    sensor_data = pd.read_csv('sensor_data.csv')

    print("Starting final PID tuning with aggressive distance control...")
    print("=" * 70)

    # Use good speed controller from previous tuning
    speed_kp_range = [2.5, 3.0, 3.5]
    speed_ki_range = [0.0, 0.01]
    speed_kd_range = [0.0]

    # Much more aggressive distance controller
    distance_kp_range = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    distance_ki_range = [0.05, 0.1, 0.2, 0.5, 1.0]
    distance_kd_range = [0.0, 0.5, 1.0, 1.5, 2.0]

    best_score = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None

    # Quick speed tuning
    print("\nPhase 1: Speed controller tuning...")
    distance_gains = [5.0, 0.2, 1.0]  # Aggressive default

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

    print(f"  Best speed: kp={best_speed_gains[0]}, ki={best_speed_gains[1]}, kd={best_speed_gains[2]}")
    print(f"  Metrics: Rise={best_metrics['rise_time']:.2f}s, Overshoot={best_metrics['overshoot']:.2f}%")

    # Intensive distance tuning
    print("\nPhase 2: Distance controller tuning...")
    speed_gains = best_speed_gains
    iteration = 0
    total_iterations = len(distance_kp_range) * len(distance_ki_range) * len(distance_kd_range)

    for kp in distance_kp_range:
        for ki in distance_ki_range:
            for kd in distance_kd_range:
                iteration += 1
                distance_gains = [kp, ki, kd]
                metrics = simulate_with_params(speed_gains, distance_gains, config.copy(), sensor_data)
                score = evaluate_performance(metrics)

                if score < best_score:
                    best_score = score
                    best_distance_gains = distance_gains
                    best_metrics = metrics
                    print(f"  [{iteration}/{total_iterations}] New best - Distance PID: [{kp:.1f}, {ki:.2f}, {kd:.1f}]")
                    print(f"      Score: {score:.2f}, Dist SS error: {metrics['dist_ss_error']:.2f}m, Min dist: {metrics['min_distance']:.2f}m")

    print("\n" + "=" * 70)
    print("FINAL TUNING RESULTS")
    print("=" * 70)
    print(f"\nOptimal Speed PID:")
    print(f"  kp = {best_speed_gains[0]}")
    print(f"  ki = {best_speed_gains[1]}")
    print(f"  kd = {best_speed_gains[2]}")
    print(f"\nOptimal Distance PID:")
    print(f"  kp = {best_distance_gains[0]}")
    print(f"  ki = {best_distance_gains[1]}")
    print(f"  kd = {best_distance_gains[2]}")

    print(f"\nPerformance Metrics:")
    print(f"  Rise time:         {best_metrics['rise_time']:.2f}s   (target < 10s)      {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot:         {best_metrics['overshoot']:.2f}%   (target < 5%)       {'✓' if best_metrics['overshoot'] < 5 else '✗'}")
    print(f"  Speed SS error:    {best_metrics['speed_ss_error']:.3f} m/s (target < 0.5 m/s) {'✓' if best_metrics['speed_ss_error'] < 0.5 else '✗'}")
    print(f"  Distance SS error: {best_metrics['dist_ss_error']:.2f}m   (target < 2m)       {'✓' if best_metrics['dist_ss_error'] < 2 else '✗'}")
    print(f"  Min distance:      {best_metrics['min_distance']:.2f}m   (target > 5m)       {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

    # Check all requirements
    all_met = (best_metrics['rise_time'] < 10 and
               best_metrics['overshoot'] < 5 and
               best_metrics['speed_ss_error'] < 0.5 and
               best_metrics['dist_ss_error'] < 2 and
               best_metrics['min_distance'] > 5)

    print(f"\nAll requirements met: {'YES ✓' if all_met else 'NO ✗'}")

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
    final_tuning()

"""Refined PID Parameter Tuning for ACC System"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_acc(config, sensor_data, dt):
    """Run ACC simulation with given configuration."""
    acc = AdaptiveCruiseControl(config)

    results = []
    ego_speed = 0.0

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0, ego_speed)

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error
        })

    return pd.DataFrame(results)


def evaluate_performance(results, set_speed):
    """Evaluate performance metrics."""
    cruise_data = results[results['mode'] == 'cruise'].copy()

    if len(cruise_data) == 0:
        return None

    # Rise time: time to reach 90% of set speed
    target_90 = 0.9 * set_speed
    rise_idx = cruise_data[cruise_data['ego_speed'] >= target_90].index
    if len(rise_idx) > 0:
        rise_time = cruise_data.loc[rise_idx[0], 'time']
    else:
        rise_time = float('inf')

    # Overshoot: maximum speed above set speed
    max_speed = cruise_data['ego_speed'].max()
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error
    final_cruise = cruise_data[cruise_data['time'] >= min(cruise_data['time'].max() - 10, 25)]
    if len(final_cruise) > 0:
        steady_state_error = abs(final_cruise['ego_speed'].mean() - set_speed)
    else:
        steady_state_error = float('inf')

    # Distance steady-state error
    follow_data = results[results['mode'] == 'follow'].copy()
    if len(follow_data) > 10:
        final_follow = follow_data.tail(min(200, len(follow_data) // 2))
        distance_ss_error = abs(final_follow['distance_error'].mean())
    else:
        distance_ss_error = 0

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'steady_state_error': steady_state_error,
        'distance_ss_error': distance_ss_error
    }


def main():
    # Load configuration and sensor data
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    sensor_data = pd.read_csv('sensor_data.csv')
    dt = base_config['simulation']['dt']
    set_speed = base_config['acc_settings']['set_speed']

    # Manual tuning based on Ziegler-Nichols and requirements
    # For speed control: need fast rise time (<10s), low overshoot (<5%), low SS error (<0.5 m/s)
    # Higher kp for faster response, moderate ki to eliminate SS error, high kd to reduce overshoot

    print("Testing refined PID parameters...")

    # Test configurations (with anti-windup, can use higher gains)
    test_configs = [
        {'speed': {'kp': 1.0, 'ki': 0.08, 'kd': 3.0}, 'distance': {'kp': 0.6, 'ki': 0.15, 'kd': 2.0}},
        {'speed': {'kp': 1.2, 'ki': 0.10, 'kd': 3.5}, 'distance': {'kp': 0.8, 'ki': 0.20, 'kd': 2.5}},
        {'speed': {'kp': 0.9, 'ki': 0.06, 'kd': 2.5}, 'distance': {'kp': 0.5, 'ki': 0.12, 'kd': 1.8}},
        {'speed': {'kp': 1.5, 'ki': 0.12, 'kd': 4.0}, 'distance': {'kp': 1.0, 'ki': 0.25, 'kd': 3.0}},
        {'speed': {'kp': 0.8, 'ki': 0.05, 'kd': 2.0}, 'distance': {'kp': 0.4, 'ki': 0.10, 'kd': 1.5}},
        {'speed': {'kp': 1.1, 'ki': 0.09, 'kd': 3.2}, 'distance': {'kp': 0.7, 'ki': 0.18, 'kd': 2.2}},
    ]

    best_config = None
    best_score = float('inf')
    best_metrics = None

    for cfg in test_configs:
        config = base_config.copy()
        config['pid_speed'] = cfg['speed']
        config['pid_distance'] = cfg['distance']

        results = simulate_acc(config, sensor_data, dt)
        metrics = evaluate_performance(results, set_speed)

        if metrics is None:
            continue

        # Scoring function emphasizing requirements
        score = 0

        # Rise time requirement: <10s
        if metrics['rise_time'] >= 10:
            score += (metrics['rise_time'] - 10) * 100

        # Overshoot requirement: <5%
        if metrics['overshoot_pct'] >= 5:
            score += (metrics['overshoot_pct'] - 5) * 50

        # Speed SS error requirement: <0.5 m/s
        if metrics['steady_state_error'] >= 0.5:
            score += (metrics['steady_state_error'] - 0.5) * 200

        # Distance SS error requirement: <2m
        if metrics['distance_ss_error'] >= 2:
            score += (metrics['distance_ss_error'] - 2) * 50

        print(f"\nSpeed PID: kp={cfg['speed']['kp']}, ki={cfg['speed']['ki']}, kd={cfg['speed']['kd']}")
        print(f"Distance PID: kp={cfg['distance']['kp']}, ki={cfg['distance']['ki']}, kd={cfg['distance']['kd']}")
        print(f"  Rise time: {metrics['rise_time']:.2f}s (req: <10s)")
        print(f"  Overshoot: {metrics['overshoot_pct']:.2f}% (req: <5%)")
        print(f"  Speed SS error: {metrics['steady_state_error']:.3f} m/s (req: <0.5 m/s)")
        print(f"  Distance SS error: {metrics['distance_ss_error']:.3f} m (req: <2m)")
        print(f"  Score: {score:.2f}")

        if score < best_score:
            best_score = score
            best_config = cfg
            best_metrics = metrics

    # Save best configuration
    tuning_results = {
        'pid_speed': best_config['speed'],
        'pid_distance': best_config['distance']
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\n" + "="*70)
    print("BEST CONFIGURATION:")
    print(f"Speed PID: kp={best_config['speed']['kp']}, ki={best_config['speed']['ki']}, kd={best_config['speed']['kd']}")
    print(f"Distance PID: kp={best_config['distance']['kp']}, ki={best_config['distance']['ki']}, kd={best_config['distance']['kd']}")
    print(f"\nPerformance metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}%")
    print(f"  Speed SS error: {best_metrics['steady_state_error']:.3f} m/s")
    print(f"  Distance SS error: {best_metrics['distance_ss_error']:.3f} m")
    print("="*70)


if __name__ == '__main__':
    main()

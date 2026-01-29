"""Refined PID tuning script for ACC system."""

import numpy as np
import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_params, distance_params, sensor_data, config, dt):
    """Run simulation with given PID parameters."""
    config['pid_speed'] = {'kp': speed_params[0], 'ki': speed_params[1], 'kd': speed_params[2]}
    config['pid_distance'] = {'kp': distance_params[0], 'ki': distance_params[1], 'kd': distance_params[2]}

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)

        results.append({
            'time': row['time'],
            'ego_speed': ego_speed,
            'accel_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance,
            'lead_speed': lead_speed
        })

    return pd.DataFrame(results)


def calculate_metrics(results_df, set_speed):
    """Calculate performance metrics."""
    metrics = {}

    # Speed metrics (cruise mode)
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    if len(cruise_data) > 10:
        # Rise time: time to reach 90% of set speed from start
        target_90 = 0.9 * set_speed
        rising = cruise_data[cruise_data['ego_speed'] < target_90]
        if len(rising) > 0 and rising['time'].iloc[-1] < 20:
            metrics['rise_time'] = rising['time'].iloc[-1]
        else:
            metrics['rise_time'] = cruise_data['time'].iloc[min(len(cruise_data)-1, int(0.9*len(cruise_data)))]

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = max(0, (max_speed - set_speed) / set_speed * 100)

        # Steady-state error (last 30% before lead vehicle appears)
        steady_idx = max(int(len(cruise_data) * 0.7), len(cruise_data) - 50)
        steady_state = cruise_data.iloc[steady_idx:]
        metrics['steady_state_error_speed'] = abs(steady_state['ego_speed'].mean() - set_speed)
    else:
        metrics['rise_time'] = 0
        metrics['overshoot_pct'] = 0
        metrics['steady_state_error_speed'] = 0

    # Distance metrics (follow mode)
    follow_data = results_df[results_df['mode'] == 'follow'].copy()

    if len(follow_data) > 10:
        valid_errors = follow_data['distance_error'].dropna()
        if len(valid_errors) > 10:
            # Steady-state distance error (last 30%)
            steady_idx = int(len(valid_errors) * 0.7)
            metrics['steady_state_error_distance'] = abs(valid_errors.iloc[steady_idx:].mean())
        else:
            metrics['steady_state_error_distance'] = abs(valid_errors.mean()) if len(valid_errors) > 0 else 0

        valid_distances = follow_data['distance'].dropna()
        metrics['min_distance'] = valid_distances.min() if len(valid_distances) > 0 else 100
    else:
        metrics['steady_state_error_distance'] = 0
        metrics['min_distance'] = 100

    return metrics


def refined_tuning():
    """Perform refined tuning with better ranges."""
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor_data = pd.read_csv('/root/sensor_data.csv')
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    print("Refined PID Tuning")
    print("=" * 60)

    # Refined ranges based on analysis
    # Speed controller: moderate P, low I, low D for smooth response without overshoot
    speed_configs = [
        (0.8, 0.02, 0.1),
        (0.9, 0.02, 0.1),
        (1.0, 0.02, 0.1),
        (1.0, 0.03, 0.1),
        (1.1, 0.02, 0.1),
        (1.2, 0.02, 0.05),
        (1.2, 0.03, 0.1),
        (1.3, 0.02, 0.1),
        (1.5, 0.02, 0.05),
    ]

    # Distance controller: higher P for responsiveness, moderate I, some D for damping
    distance_configs = [
        (0.8, 0.05, 0.5),
        (1.0, 0.05, 0.5),
        (1.2, 0.05, 0.5),
        (1.5, 0.05, 0.5),
        (1.5, 0.08, 0.5),
        (1.8, 0.05, 0.5),
        (2.0, 0.05, 0.5),
        (2.0, 0.08, 0.5),
        (2.5, 0.05, 0.5),
    ]

    best_cost = float('inf')
    best_speed = None
    best_distance = None
    best_metrics = None
    best_results = None

    total = len(speed_configs) * len(distance_configs)
    count = 0

    for speed_params in speed_configs:
        for distance_params in distance_configs:
            count += 1
            if count % 10 == 0:
                print(f"Progress: {count}/{total}")

            results_df = simulate_with_params(speed_params, distance_params, sensor_data, config, dt)
            metrics = calculate_metrics(results_df, set_speed)

            # Cost function
            cost = 0
            cost += max(0, metrics['rise_time'] - 10) * 20
            cost += max(0, metrics['overshoot_pct'] - 5) * 10
            cost += max(0, metrics['steady_state_error_speed'] - 0.5) * 50
            cost += max(0, metrics['steady_state_error_distance'] - 2.0) * 30
            cost += max(0, 5.0 - metrics['min_distance']) * 100

            # Preference terms
            cost += metrics['overshoot_pct'] * 2
            cost += metrics['steady_state_error_speed'] * 5
            cost += metrics['steady_state_error_distance'] * 2

            if cost < best_cost:
                best_cost = cost
                best_speed = speed_params
                best_distance = distance_params
                best_metrics = metrics
                best_results = results_df

    print("\n" + "=" * 60)
    print("Best Parameters Found:")
    print("=" * 60)
    print(f"Speed PID: kp={best_speed[0]}, ki={best_speed[1]}, kd={best_speed[2]}")
    print(f"Distance PID: kp={best_distance[0]}, ki={best_distance[1]}, kd={best_distance[2]}")
    print(f"\nCost: {best_cost:.2f}")
    print("\nPerformance Metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {best_metrics['steady_state_error_speed']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance SS error: {best_metrics['steady_state_error_distance']:.3f} m (target: <2m)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m)")

    # Save results
    tuning_results = {
        'pid_speed': {
            'kp': float(best_speed[0]),
            'ki': float(best_speed[1]),
            'kd': float(best_speed[2])
        },
        'pid_distance': {
            'kp': float(best_distance[0]),
            'ki': float(best_distance[1]),
            'kd': float(best_distance[2])
        }
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    refined_tuning()

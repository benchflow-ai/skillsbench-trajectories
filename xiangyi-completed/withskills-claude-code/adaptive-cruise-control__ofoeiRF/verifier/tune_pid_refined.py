"""Refined PID parameter tuning script for ACC system."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_kp, speed_ki, speed_kd, distance_kp, distance_ki, distance_kd):
    """Run simulation with given PID parameters and return performance metrics."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Override PID parameters
    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
    config['pid_distance'] = {'kp': distance_kp, 'ki': distance_ki, 'kd': distance_kd}

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    # Simulation state
    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        results.append({
            'time': row['time'],
            'ego_speed': ego_speed,
            'accel_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance
        })

    df = pd.DataFrame(results)

    # Calculate performance metrics
    metrics = {}

    # Speed metrics (cruise phase before lead vehicle appears)
    cruise_data = df[df['mode'] == 'cruise'].copy()
    if len(cruise_data) > 0:
        # Rise time: time to reach 90% of set speed
        target_90 = 0.9 * set_speed
        rise_data = cruise_data[cruise_data['ego_speed'] >= target_90]
        if len(rise_data) > 0:
            metrics['rise_time'] = rise_data.iloc[0]['time']
        else:
            metrics['rise_time'] = 999.0

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = max(0, (max_speed - set_speed) / set_speed * 100)

        # Steady-state error (last 5 seconds of cruise mode)
        steady_cruise = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 5.0]
        if len(steady_cruise) > 0:
            metrics['speed_ss_error'] = abs(steady_cruise['ego_speed'].mean() - set_speed)
        else:
            metrics['speed_ss_error'] = 999.0
    else:
        metrics['rise_time'] = 999.0
        metrics['overshoot_pct'] = 999.0
        metrics['speed_ss_error'] = 999.0

    # Distance metrics (follow phase)
    follow_data = df[(df['mode'] == 'follow') & (df['distance_error'].notna())].copy()
    if len(follow_data) > 30:
        # Distance steady-state error (last 30% of follow mode)
        n_samples = len(follow_data)
        steady_follow = follow_data.iloc[int(0.7 * n_samples):]
        metrics['distance_ss_error'] = abs(steady_follow['distance_error'].mean())

        # Minimum distance maintained
        metrics['min_distance'] = follow_data['distance'].min()
    else:
        metrics['distance_ss_error'] = 0.0
        metrics['min_distance'] = 999.0

    # Combined cost function - weighted to emphasize meeting all targets
    cost = 0.0
    cost += max(0, metrics['rise_time'] - 10.0) * 20.0  # Penalty if rise time > 10s
    cost += max(0, metrics['overshoot_pct'] - 5.0) * 10.0  # Penalty if overshoot > 5%
    cost += max(0, metrics['speed_ss_error'] - 0.5) * 50.0  # Penalty if ss error > 0.5 m/s
    cost += max(0, metrics['distance_ss_error'] - 2.0) * 30.0  # Penalty if distance error > 2m
    cost += max(0, 5.0 - metrics['min_distance']) * 100.0  # Heavy penalty if min distance < 5m

    # Add baseline costs for optimization
    cost += metrics['rise_time'] * 0.3
    cost += metrics['overshoot_pct'] * 0.5
    cost += metrics['speed_ss_error'] * 5.0
    cost += abs(metrics['distance_ss_error']) * 8.0  # Heavily weight distance error

    metrics['cost'] = cost
    return metrics, df


def tune_pid_refined():
    """Refined PID tuning with focused search."""
    print("Starting refined PID parameter tuning...")

    # Refined search space based on initial results
    speed_kp_range = [2.0, 2.5, 3.0, 3.5, 4.0]
    speed_ki_range = [0.0, 0.01, 0.05, 0.1]
    speed_kd_range = [0.0, 0.05, 0.1, 0.2]

    distance_kp_range = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    distance_ki_range = [0.0, 0.005, 0.01, 0.02, 0.05]
    distance_kd_range = [0.0, 0.2, 0.5, 1.0, 1.5, 2.0]

    best_cost = float('inf')
    best_params = None
    best_metrics = None

    # Grid search for speed PID (keeping it simple based on initial results)
    print("\nTuning speed PID controller...")
    for kp in speed_kp_range:
        for ki in speed_ki_range:
            for kd in speed_kd_range:
                metrics, _ = simulate_with_params(kp, ki, kd, 1.0, 0.01, 0.5)
                if metrics['cost'] < best_cost:
                    best_cost = metrics['cost']
                    best_params = {'speed': (kp, ki, kd), 'distance': (1.0, 0.01, 0.5)}
                    best_metrics = metrics
                    print(f"  Speed PID: kp={kp}, ki={ki}, kd={kd} | Rise={metrics['rise_time']:.2f}s, Overshoot={metrics['overshoot_pct']:.2f}%, Cost={metrics['cost']:.2f}")

    speed_params = best_params['speed']
    print(f"\nBest speed PID: kp={speed_params[0]}, ki={speed_params[1]}, kd={speed_params[2]}")

    # Comprehensive grid search for distance PID
    print("\nTuning distance PID controller...")
    best_cost = float('inf')
    for kp in distance_kp_range:
        for ki in distance_ki_range:
            for kd in distance_kd_range:
                metrics, _ = simulate_with_params(speed_params[0], speed_params[1], speed_params[2], kp, ki, kd)
                if metrics['cost'] < best_cost:
                    best_cost = metrics['cost']
                    best_params = {'speed': speed_params, 'distance': (kp, ki, kd)}
                    best_metrics = metrics
                    print(f"  Distance PID: kp={kp}, ki={ki}, kd={kd} | Dist_err={metrics['distance_ss_error']:.2f}m, Min_dist={metrics['min_distance']:.2f}m, Cost={metrics['cost']:.2f}")

    print("\n" + "="*80)
    print("FINAL TUNED PARAMETERS:")
    print("="*80)
    print(f"Speed PID: kp={best_params['speed'][0]}, ki={best_params['speed'][1]}, kd={best_params['speed'][2]}")
    print(f"Distance PID: kp={best_params['distance'][0]}, ki={best_params['distance'][1]}, kd={best_params['distance'][2]}")
    print("\nPerformance Metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.4f} m/s (target: <0.5 m/s)")
    print(f"  Distance SS error: {best_metrics['distance_ss_error']:.2f} m (target: <2m)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m)")
    print(f"  Total cost: {best_metrics['cost']:.2f}")

    # Save tuned parameters
    tuned_config = {
        'pid_speed': {
            'kp': float(best_params['speed'][0]),
            'ki': float(best_params['speed'][1]),
            'kd': float(best_params['speed'][2])
        },
        'pid_distance': {
            'kp': float(best_params['distance'][0]),
            'ki': float(best_params['distance'][1]),
            'kd': float(best_params['distance'][2])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuned_config, f, default_flow_style=False)

    print("\nTuned parameters saved to tuning_results.yaml")
    return best_params, best_metrics


if __name__ == '__main__':
    tune_pid_refined()

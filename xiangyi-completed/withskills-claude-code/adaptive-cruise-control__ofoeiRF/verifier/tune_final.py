"""Final PID parameter tuning for ACC system with improved control strategy."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_kp, speed_ki, speed_kd, distance_kp, distance_ki, distance_kd):
    """Run simulation with given PID parameters and return performance metrics."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
    config['pid_distance'] = {'kp': distance_kp, 'ki': distance_ki, 'kd': distance_kd}

    sensor_data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
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
    metrics = {}

    # Speed metrics - cruise phase
    cruise_data = df[df['mode'] == 'cruise'].copy()
    if len(cruise_data) > 0:
        target_90 = 0.9 * set_speed
        rise_data = cruise_data[cruise_data['ego_speed'] >= target_90]
        metrics['rise_time'] = rise_data.iloc[0]['time'] if len(rise_data) > 0 else 999.0

        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = max(0, (max_speed - set_speed) / set_speed * 100)

        steady_cruise = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 5.0]
        metrics['speed_ss_error'] = abs(steady_cruise['ego_speed'].mean() - set_speed) if len(steady_cruise) > 0 else 999.0
    else:
        metrics['rise_time'] = 999.0
        metrics['overshoot_pct'] = 999.0
        metrics['speed_ss_error'] = 999.0

    # Distance metrics - follow phase
    follow_data = df[(df['mode'] == 'follow') & (df['distance_error'].notna())].copy()
    if len(follow_data) > 30:
        n_samples = len(follow_data)
        steady_follow = follow_data.iloc[int(0.7 * n_samples):]
        metrics['distance_ss_error'] = abs(steady_follow['distance_error'].mean())
        metrics['min_distance'] = follow_data['distance'].min()
    else:
        metrics['distance_ss_error'] = 0.0
        metrics['min_distance'] = 999.0

    # Cost function
    cost = 0.0
    cost += max(0, metrics['rise_time'] - 10.0) * 100.0
    cost += max(0, metrics['overshoot_pct'] - 5.0) * 20.0
    cost += max(0, metrics['speed_ss_error'] - 0.5) * 100.0
    cost += max(0, metrics['distance_ss_error'] - 2.0) * 50.0
    cost += max(0, 5.0 - metrics['min_distance']) * 200.0

    cost += metrics['rise_time'] * 0.2
    cost += metrics['overshoot_pct'] * 0.5
    cost += metrics['speed_ss_error'] * 10.0
    cost += abs(metrics['distance_ss_error']) * 15.0

    metrics['cost'] = cost
    return metrics


def tune_final():
    """Final PID tuning with optimized search."""
    print("Starting final PID parameter tuning...")

    # Search ranges
    speed_kp_vals = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    speed_ki_vals = [0.0, 0.01, 0.05, 0.1]
    speed_kd_vals = [0.0, 0.05, 0.1]

    distance_kp_vals = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
    distance_ki_vals = [0.0, 0.001, 0.005, 0.01, 0.02]
    distance_kd_vals = [0.0, 0.1, 0.2, 0.5, 1.0]

    best_cost = float('inf')
    best_params = None
    best_metrics = None

    print("\n=== Tuning Speed PID ===")
    for kp in speed_kp_vals:
        for ki in speed_ki_vals:
            for kd in speed_kd_vals:
                metrics = simulate_with_params(kp, ki, kd, 0.3, 0.005, 0.2)
                if metrics['cost'] < best_cost:
                    best_cost = metrics['cost']
                    best_params = {'speed': (kp, ki, kd), 'distance': (0.3, 0.005, 0.2)}
                    best_metrics = metrics
                    print(f"  kp={kp:.1f}, ki={ki:.3f}, kd={kd:.2f} -> Rise={metrics['rise_time']:.2f}s, Over={metrics['overshoot_pct']:.2f}%, SS_err={metrics['speed_ss_error']:.3f}, Cost={metrics['cost']:.1f}")

    speed_best = best_params['speed']
    print(f"\nBest Speed PID: kp={speed_best[0]}, ki={speed_best[1]}, kd={speed_best[2]}")

    print("\n=== Tuning Distance PID ===")
    best_cost = float('inf')
    for kp in distance_kp_vals:
        for ki in distance_ki_vals:
            for kd in distance_kd_vals:
                metrics = simulate_with_params(speed_best[0], speed_best[1], speed_best[2], kp, ki, kd)
                if metrics['cost'] < best_cost:
                    best_cost = metrics['cost']
                    best_params = {'speed': speed_best, 'distance': (kp, ki, kd)}
                    best_metrics = metrics
                    print(f"  kp={kp:.2f}, ki={ki:.3f}, kd={kd:.2f} -> Dist_err={metrics['distance_ss_error']:.2f}m, Min={metrics['min_distance']:.2f}m, Cost={metrics['cost']:.1f}")

    print("\n" + "="*80)
    print("FINAL TUNED PARAMETERS")
    print("="*80)
    print(f"Speed PID:    kp={best_params['speed'][0]}, ki={best_params['speed'][1]}, kd={best_params['speed'][2]}")
    print(f"Distance PID: kp={best_params['distance'][0]}, ki={best_params['distance'][1]}, kd={best_params['distance'][2]}")
    print("\nPerformance:")
    print(f"  Rise time:        {best_metrics['rise_time']:.2f}s  (target: <10s)")
    print(f"  Overshoot:        {best_metrics['overshoot_pct']:.2f}%  (target: <5%)")
    print(f"  Speed SS error:   {best_metrics['speed_ss_error']:.4f} m/s  (target: <0.5 m/s)")
    print(f"  Distance SS err:  {best_metrics['distance_ss_error']:.2f} m  (target: <2m)")
    print(f"  Min distance:     {best_metrics['min_distance']:.2f} m  (target: >5m)")

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

    print("\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    tune_final()

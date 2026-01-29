"""Final PID tuning with focus on meeting all requirements."""

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

    # Speed metrics (cruise mode only)
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    if len(cruise_data) > 10:
        # Rise time: time to first reach 90% of set speed
        target_90 = 0.9 * set_speed
        above_90 = cruise_data[cruise_data['ego_speed'] >= target_90]
        if len(above_90) > 0:
            metrics['rise_time'] = above_90['time'].iloc[0]
        else:
            metrics['rise_time'] = cruise_data['time'].iloc[-1]

        # Overshoot: max speed relative to set speed
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = max(0, (max_speed - set_speed) / set_speed * 100)

        # Steady-state error: average error in last 20% of cruise period
        steady_idx = int(len(cruise_data) * 0.8)
        if steady_idx < len(cruise_data) - 1:
            steady_state = cruise_data.iloc[steady_idx:]
            metrics['steady_state_error_speed'] = abs(steady_state['ego_speed'].mean() - set_speed)
        else:
            metrics['steady_state_error_speed'] = abs(cruise_data['ego_speed'].iloc[-1] - set_speed)
    else:
        metrics['rise_time'] = 0
        metrics['overshoot_pct'] = 0
        metrics['steady_state_error_speed'] = 0

    # Distance metrics (follow mode only)
    follow_data = results_df[results_df['mode'] == 'follow'].copy()

    if len(follow_data) > 10:
        valid_errors = follow_data['distance_error'].dropna()
        if len(valid_errors) > 10:
            # Steady-state: last 20% of following period
            steady_idx = int(len(valid_errors) * 0.8)
            metrics['steady_state_error_distance'] = abs(valid_errors.iloc[steady_idx:].mean())
        else:
            metrics['steady_state_error_distance'] = abs(valid_errors.mean()) if len(valid_errors) > 0 else 0

        valid_distances = follow_data['distance'].dropna()
        metrics['min_distance'] = valid_distances.min() if len(valid_distances) > 0 else 100
    else:
        metrics['steady_state_error_distance'] = 0
        metrics['min_distance'] = 100

    return metrics


def comprehensive_tuning():
    """Comprehensive tuning to meet all requirements."""
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor_data = pd.read_csv('/root/sensor_data.csv')
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    print("Comprehensive PID Tuning")
    print("=" * 60)

    # Key insight: Low P gain reduces overshoot, adequate I ensures reaching setpoint
    # Speed controller - prioritize low overshoot
    speed_configs = [
        # (kp, ki, kd)
        (0.5, 0.05, 0.0),
        (0.6, 0.05, 0.0),
        (0.7, 0.05, 0.0),
        (0.8, 0.05, 0.0),
        (0.8, 0.06, 0.0),
        (0.9, 0.05, 0.0),
        (0.9, 0.06, 0.0),
        (1.0, 0.04, 0.0),
        (1.0, 0.05, 0.0),
    ]

    # Distance controller - need responsive tracking
    distance_configs = [
        (1.0, 0.1, 0.8),
        (1.2, 0.1, 0.8),
        (1.5, 0.1, 0.8),
        (1.5, 0.1, 1.0),
        (1.8, 0.1, 1.0),
        (2.0, 0.1, 1.0),
        (2.0, 0.15, 1.0),
        (2.5, 0.1, 1.0),
    ]

    best_cost = float('inf')
    best_speed = None
    best_distance = None
    best_metrics = None

    total = len(speed_configs) * len(distance_configs)
    count = 0

    for speed_params in speed_configs:
        for distance_params in distance_configs:
            count += 1
            if count % 10 == 0:
                print(f"Progress: {count}/{total} (best cost: {best_cost:.2f})")

            results_df = simulate_with_params(speed_params, distance_params, sensor_data, config, dt)
            metrics = calculate_metrics(results_df, set_speed)

            # Strict cost function - heavy penalties for requirement violations
            cost = 0

            # Hard constraints with severe penalties
            if metrics['rise_time'] > 10:
                cost += (metrics['rise_time'] - 10) * 100
            if metrics['overshoot_pct'] > 5:
                cost += (metrics['overshoot_pct'] - 5) * 50
            if metrics['steady_state_error_speed'] > 0.5:
                cost += (metrics['steady_state_error_speed'] - 0.5) * 200
            if metrics['steady_state_error_distance'] > 2.0:
                cost += (metrics['steady_state_error_distance'] - 2.0) * 100
            if metrics['min_distance'] < 5.0:
                cost += (5.0 - metrics['min_distance']) * 500

            # Optimization objectives (minimize even if within limits)
            cost += metrics['rise_time'] * 1
            cost += metrics['overshoot_pct'] * 5
            cost += metrics['steady_state_error_speed'] * 10
            cost += metrics['steady_state_error_distance'] * 5

            if cost < best_cost:
                best_cost = cost
                best_speed = speed_params
                best_distance = distance_params
                best_metrics = metrics

                # Print when we find a better solution
                print(f"\n  New best at iteration {count}:")
                print(f"    Speed: kp={speed_params[0]}, ki={speed_params[1]}, kd={speed_params[2]}")
                print(f"    Distance: kp={distance_params[0]}, ki={distance_params[1]}, kd={distance_params[2]}")
                print(f"    Rise: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot_pct']:.2f}%, " +
                      f"SS_speed: {metrics['steady_state_error_speed']:.3f}, " +
                      f"SS_dist: {metrics['steady_state_error_distance']:.3f}, " +
                      f"Min_dist: {metrics['min_distance']:.2f}")

    print("\n" + "=" * 60)
    print("FINAL TUNING RESULTS")
    print("=" * 60)
    print(f"\nSpeed PID: kp={best_speed[0]}, ki={best_speed[1]}, kd={best_speed[2]}")
    print(f"Distance PID: kp={best_distance[0]}, ki={best_distance[1]}, kd={best_distance[2]}")
    print(f"\nFinal Cost: {best_cost:.2f}")
    print("\n" + "-" * 60)
    print("Performance vs Requirements:")
    print("-" * 60)
    print(f"Rise time:        {best_metrics['rise_time']:6.2f}s  (requirement: <10s)    {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"Overshoot:        {best_metrics['overshoot_pct']:6.2f}%  (requirement: <5%)     {'✓' if best_metrics['overshoot_pct'] < 5 else '✗'}")
    print(f"Speed SS error:   {best_metrics['steady_state_error_speed']:6.3f} m/s (requirement: <0.5)   {'✓' if best_metrics['steady_state_error_speed'] < 0.5 else '✗'}")
    print(f"Distance SS error:{best_metrics['steady_state_error_distance']:6.3f} m   (requirement: <2m)    {'✓' if best_metrics['steady_state_error_distance'] < 2 else '✗'}")
    print(f"Min distance:     {best_metrics['min_distance']:6.2f} m   (requirement: >5m)    {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

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

    print("\n✓ Results saved to tuning_results.yaml")


if __name__ == '__main__':
    comprehensive_tuning()

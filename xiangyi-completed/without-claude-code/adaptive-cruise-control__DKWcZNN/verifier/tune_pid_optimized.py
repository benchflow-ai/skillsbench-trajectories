"""Optimized PID tuning focusing on actual requirements."""

import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_params, distance_params, sensor_data, config, dt):
    """Run full simulation with given parameters."""
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


def evaluate_performance(results_df, set_speed):
    """Evaluate against all requirements."""
    metrics = {}
    passed = {}

    # 1. Speed rise time < 10s (cruise mode)
    cruise_data = results_df[results_df['mode'] == 'cruise']
    if len(cruise_data) > 0:
        target_90 = 0.9 * set_speed
        above_90 = cruise_data[cruise_data['ego_speed'] >= target_90]
        metrics['rise_time'] = above_90['time'].iloc[0] if len(above_90) > 0 else 999
        passed['rise_time'] = metrics['rise_time'] < 10

        # 2. Overshoot < 5%
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = max(0, (max_speed - set_speed) / set_speed * 100)
        passed['overshoot'] = metrics['overshoot_pct'] < 5

        # 3. Speed steady-state error < 0.5 m/s
        # Take last 10% of cruise mode before lead vehicle appears
        steady_start = int(len(cruise_data) * 0.9)
        steady_state = cruise_data.iloc[steady_start:]
        metrics['speed_ss_error'] = abs(steady_state['ego_speed'].mean() - set_speed)
        passed['speed_ss'] = metrics['speed_ss_error'] < 0.5
    else:
        metrics['rise_time'] = 999
        metrics['overshoot_pct'] = 0
        metrics['speed_ss_error'] = 999
        passed['rise_time'] = False
        passed['overshoot'] = False
        passed['speed_ss'] = False

    # 4. Distance steady-state error < 2m (follow mode)
    follow_data = results_df[results_df['mode'] == 'follow']
    if len(follow_data) > 20:
        valid_errors = follow_data['distance_error'].dropna()
        if len(valid_errors) > 20:
            # Take last 10% of follow mode
            steady_start = int(len(valid_errors) * 0.9)
            metrics['distance_ss_error'] = abs(valid_errors.iloc[steady_start:].mean())
            passed['distance_ss'] = metrics['distance_ss_error'] < 2.0
        else:
            metrics['distance_ss_error'] = 999
            passed['distance_ss'] = False
    else:
        metrics['distance_ss_error'] = 999
        passed['distance_ss'] = False

    # 5. Minimum distance > 5m
    all_distances = results_df['distance'].dropna()
    if len(all_distances) > 0:
        metrics['min_distance'] = all_distances.min()
        passed['min_distance'] = metrics['min_distance'] > 5
    else:
        metrics['min_distance'] = 999
        passed['min_distance'] = True

    return metrics, passed


def optimized_tuning():
    """Optimized tuning approach."""
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor_data = pd.read_csv('/root/sensor_data.csv')
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    print("Optimized PID Tuning for ACC System")
    print("=" * 70)

    # Strategy: Start conservative to avoid overshoot, then increase distance gains
    # Speed: Low kp to prevent overshoot, sufficient ki to reach setpoint
    speed_candidates = [
        (0.5, 0.04, 0.0),
        (0.5, 0.05, 0.0),
        (0.6, 0.04, 0.0),
        (0.6, 0.05, 0.0),
        (0.7, 0.04, 0.0),
    ]

    # Distance: High gains needed to prevent collision
    distance_candidates = [
        (3.0, 0.2, 1.5),
        (3.5, 0.2, 1.5),
        (4.0, 0.2, 1.5),
        (4.0, 0.3, 1.5),
        (4.5, 0.2, 1.5),
        (5.0, 0.2, 1.5),
        (5.0, 0.3, 1.5),
        (6.0, 0.2, 1.5),
    ]

    best_score = -1
    best_speed = None
    best_distance = None
    best_metrics = None
    all_passed = False

    total = len(speed_candidates) * len(distance_candidates)
    tested = 0

    for speed_params in speed_candidates:
        for distance_params in distance_candidates:
            tested += 1

            results_df = simulate_with_params(speed_params, distance_params, sensor_data, config, dt)
            metrics, passed = evaluate_performance(results_df, set_speed)

            # Score: count how many requirements passed
            score = sum(passed.values())

            # If all passed, prefer lower gains for smoother control
            if score == 5:  # All requirements met
                smoothness = -speed_params[0] - distance_params[0]  # Prefer lower gains
                score += smoothness * 0.01

            if score > best_score or (score == best_score and not all_passed):
                best_score = score
                best_speed = speed_params
                best_distance = distance_params
                best_metrics = metrics
                all_passed = all(passed.values())

                if all_passed:
                    print(f"\n✓ Found solution at {tested}/{total}:")
                    print(f"  Speed: kp={speed_params[0]}, ki={speed_params[1]}, kd={speed_params[2]}")
                    print(f"  Dist: kp={distance_params[0]}, ki={distance_params[1]}, kd={distance_params[2]}")
                    print(f"  Metrics: RT={metrics['rise_time']:.2f}s, OS={metrics['overshoot_pct']:.2f}%, " +
                          f"SS_v={metrics['speed_ss_error']:.3f}, SS_d={metrics['distance_ss_error']:.3f}, " +
                          f"min_d={metrics['min_distance']:.2f}m")
                    break

        if all_passed:
            break

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"\nSpeed PID:    kp={best_speed[0]}, ki={best_speed[1]}, kd={best_speed[2]}")
    print(f"Distance PID: kp={best_distance[0]}, ki={best_distance[1]}, kd={best_distance[2]}")

    print("\n" + "-" * 70)
    print("Requirement Verification:")
    print("-" * 70)

    results_df = simulate_with_params(best_speed, best_distance, sensor_data, config, dt)
    metrics, passed = evaluate_performance(results_df, set_speed)

    checks = [
        ("Rise time < 10s", metrics['rise_time'], "<10s", passed['rise_time']),
        ("Overshoot < 5%", metrics['overshoot_pct'], "<5%", passed['overshoot']),
        ("Speed SS error < 0.5 m/s", metrics['speed_ss_error'], "<0.5", passed['speed_ss']),
        ("Distance SS error < 2m", metrics['distance_ss_error'], "<2m", passed['distance_ss']),
        ("Min distance > 5m", metrics['min_distance'], ">5m", passed['min_distance']),
    ]

    for name, value, target, check in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"{name:30s} {value:8.3f} {target:8s} {status}")

    if all(passed.values()):
        print("\n✓ ALL REQUIREMENTS MET")
    else:
        print(f"\n⚠ {sum(passed.values())}/5 requirements met")

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
    optimized_tuning()

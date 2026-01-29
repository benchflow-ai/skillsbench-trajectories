"""Safe PID tuning with focus on meeting all constraints."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def simulate(speed_params, dist_params):
    """Run simulation and return metrics."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['pid_speed'] = {'kp': speed_params[0], 'ki': speed_params[1], 'kd': speed_params[2]}
    config['pid_distance'] = {'kp': dist_params[0], 'ki': dist_params[1], 'kd': dist_params[2]}

    sensor_data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']
    time_headway = config['acc_settings']['time_headway']
    min_distance_cfg = config['acc_settings']['min_distance']

    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Check if in active follow
        active_follow = False
        if distance is not None and lead_speed is not None:
            desired_dist = ego_speed * time_headway + min_distance_cfg
            active_follow = distance < 2.0 * desired_dist

        results.append({
            'time': row['time'],
            'ego_speed': ego_speed,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'active_follow': active_follow
        })

    df = pd.DataFrame(results)

    # Metrics
    cruise = df[df['mode'] == 'cruise']
    if len(cruise) > 0:
        target_90 = 0.9 * set_speed
        rise_data = cruise[cruise['ego_speed'] >= target_90]
        rise_time = rise_data.iloc[0]['time'] if len(rise_data) > 0 else 999.0
        overshoot_pct = max(0, (cruise['ego_speed'].max() - set_speed) / set_speed * 100)
        steady = cruise[cruise['time'] >= cruise['time'].max() - 5.0]
        speed_ss_error = abs(steady['ego_speed'].mean() - set_speed) if len(steady) > 0 else 999.0
    else:
        rise_time, overshoot_pct, speed_ss_error = 999.0, 999.0, 999.0

    active_follow = df[(df['active_follow'] == True) & (df['distance_error'].notna())]
    if len(active_follow) > 20:
        n = len(active_follow)
        steady_follow = active_follow.iloc[int(0.7 * n):]
        distance_ss_error = abs(steady_follow['distance_error'].mean())
    else:
        distance_ss_error = 0.0

    all_follow = df[(df['mode'] == 'follow') & (df['distance'].notna())]
    min_distance_val = all_follow['distance'].min() if len(all_follow) > 0 else 999.0

    # Check all constraints
    constraints_met = {
        'rise_time': rise_time < 10.0,
        'overshoot': overshoot_pct < 5.0,
        'speed_ss': speed_ss_error < 0.5,
        'distance_ss': distance_ss_error < 2.0,
        'min_distance': min_distance_val > 5.0
    }

    # Penalty for violations
    score = 0.0
    if not constraints_met['rise_time']:
        score += (rise_time - 10.0) * 200.0
    if not constraints_met['overshoot']:
        score += (overshoot_pct - 5.0) * 100.0
    if not constraints_met['speed_ss']:
        score += (speed_ss_error - 0.5) * 500.0
    if not constraints_met['distance_ss']:
        score += (distance_ss_error - 2.0) * 200.0
    if not constraints_met['min_distance']:
        score += (5.0 - min_distance_val) * 1000.0  # CRITICAL

    # Base costs
    score += rise_time * 1.0 + overshoot_pct * 2.0 + speed_ss_error * 50.0 + distance_ss_error * 50.0

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance_val,
        'constraints_met': all(constraints_met.values()),
        'score': score
    }


def main():
    """Run safe PID tuning."""
    print("Safe PID Tuning - All Constraints Must Be Met")
    print("="*70)

    # Conservative speed PID - avoid overshoot
    speed_options = [
        (2.5, 0.0, 0.05), (3.0, 0.0, 0.05), (3.5, 0.0, 0.0), (4.0, 0.0, 0.0),
        (2.5, 0.01, 0.1), (3.0, 0.01, 0.1), (3.5, 0.01, 0.05), (4.0, 0.01, 0.05)
    ]

    # Conservative distance PID - ensure min distance > 5m
    distance_options = [
        (0.3, 0.005, 0.5), (0.5, 0.005, 0.5), (0.8, 0.005, 0.5),
        (0.3, 0.01, 1.0), (0.5, 0.01, 1.0), (0.8, 0.01, 1.0), (1.0, 0.01, 1.0),
        (0.5, 0.02, 1.5), (0.8, 0.02, 1.5), (1.0, 0.02, 1.5),
        (0.5, 0.0, 0.5), (0.8, 0.0, 0.5), (1.0, 0.0, 0.5)
    ]

    best_score = float('inf')
    best_params = None
    best_metrics = None
    valid_solutions = []

    print("\nSearching for valid parameter combinations...")
    for sp in speed_options:
        for dp in distance_options:
            m = simulate(sp, dp)
            if m['constraints_met']:
                valid_solutions.append((sp, dp, m))
                print(f"✓ VALID: Sp{sp} Ds{dp} -> R={m['rise_time']:.1f}s O={m['overshoot_pct']:.1f}% "
                      f"SpSS={m['speed_ss_error']:.3f} DsSS={m['distance_ss_error']:.2f}m MinD={m['min_distance']:.1f}m")

            if m['score'] < best_score:
                best_score = m['score']
                best_params = {'speed': sp, 'distance': dp}
                best_metrics = m

    sp = best_params['speed']
    dp = best_params['distance']

    print("\n" + "="*80)
    if best_metrics['constraints_met']:
        print("SUCCESS: Found valid solution meeting ALL constraints!")
    else:
        print("BEST EFFORT: Constraints not fully met, using best available")
    print("="*80)
    print(f"Speed PID:    kp={sp[0]}, ki={sp[1]}, kd={sp[2]}")
    print(f"Distance PID: kp={dp[0]}, ki={dp[1]}, kd={dp[2]}")
    print(f"\nPerformance:")
    print(f"  Rise time:        {best_metrics['rise_time']:.2f} s  (< 10s)   {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot:        {best_metrics['overshoot_pct']:.2f} %  (< 5%)    {'✓' if best_metrics['overshoot_pct'] < 5 else '✗'}")
    print(f"  Speed SS error:   {best_metrics['speed_ss_error']:.4f} m/s  (< 0.5)  {'✓' if best_metrics['speed_ss_error'] < 0.5 else '✗'}")
    print(f"  Distance SS err:  {best_metrics['distance_ss_error']:.2f} m  (< 2m)   {'✓' if best_metrics['distance_ss_error'] < 2 else '✗'}")
    print(f"  Min distance:     {best_metrics['min_distance']:.2f} m  (> 5m)   {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

    if valid_solutions:
        print(f"\nFound {len(valid_solutions)} valid solution(s) meeting all constraints")

    result = {
        'pid_speed': {'kp': float(sp[0]), 'ki': float(sp[1]), 'kd': float(sp[2])},
        'pid_distance': {'kp': float(dp[0]), 'ki': float(dp[1]), 'kd': float(dp[2])}
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(result, f, default_flow_style=False)

    print("\n✓ Saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

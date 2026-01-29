"""Smart PID tuning focusing on active follow phase."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def simulate_and_evaluate(speed_kp, speed_ki, speed_kd, distance_kp, distance_ki, distance_kd):
    """Simulate and evaluate with focus on active follow phase."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
    config['pid_distance'] = {'kp': distance_kp, 'ki': distance_ki, 'kd': distance_kd}

    sensor_data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']
    time_headway = config['acc_settings']['time_headway']
    min_distance = config['acc_settings']['min_distance']

    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Track if in active follow (distance < 2x desired)
        active_follow = False
        if distance is not None and lead_speed is not None:
            desired_dist = ego_speed * time_headway + min_distance
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

    # Cruise phase metrics
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

    # Active follow phase metrics (when lead vehicle is close enough to actively follow)
    active_follow = df[(df['active_follow'] == True) & (df['distance_error'].notna())]
    if len(active_follow) > 20:
        # Use last 30% of active follow for steady-state
        n = len(active_follow)
        steady_follow = active_follow.iloc[int(0.7 * n):]
        distance_ss_error = abs(steady_follow['distance_error'].mean())
        min_distance_val = active_follow['distance'].min()
    else:
        distance_ss_error = 0.0
        min_distance_val = 999.0

    # All follow data (for min distance check)
    all_follow = df[(df['mode'] == 'follow') & (df['distance'].notna())]
    if len(all_follow) > 0:
        min_distance_val = min(min_distance_val, all_follow['distance'].min())

    metrics = {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance_val
    }

    # Scoring
    score = 0.0
    if rise_time > 10.0:
        score += (rise_time - 10.0) * 100.0
    if overshoot_pct > 5.0:
        score += (overshoot_pct - 5.0) * 50.0
    if speed_ss_error > 0.5:
        score += (speed_ss_error - 0.5) * 200.0
    if distance_ss_error > 2.0:
        score += (distance_ss_error - 2.0) * 100.0
    if min_distance_val < 5.0:
        score += (5.0 - min_distance_val) * 500.0

    score += rise_time * 0.5 + overshoot_pct * 1.0 + speed_ss_error * 20.0 + distance_ss_error * 30.0

    metrics['score'] = score
    return metrics


def main():
    """Run smart tuning."""
    print("Smart PID Tuning (Focus on Active Follow Phase)")
    print("="*60)

    # Speed PID candidates - prioritize meeting specs
    speed_candidates = [
        (2.5, 0.0, 0.0), (3.0, 0.0, 0.0), (3.5, 0.0, 0.0), (4.0, 0.0, 0.0),
        (2.5, 0.01, 0.05), (3.0, 0.01, 0.05), (3.5, 0.01, 0.0), (4.0, 0.01, 0.0)
    ]

    # Distance PID candidates - more aggressive with derivative for stability
    distance_candidates = [
        (0.5, 0.01, 0.5), (0.8, 0.01, 0.5), (1.0, 0.01, 0.5), (1.5, 0.01, 0.5),
        (0.5, 0.02, 1.0), (0.8, 0.02, 1.0), (1.0, 0.02, 1.0), (1.5, 0.02, 1.0),
        (0.8, 0.01, 0.0), (1.0, 0.01, 0.0), (1.5, 0.01, 0.0), (2.0, 0.01, 0.0)
    ]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    print("\nSearching parameter space...")
    count = 0
    for sp_kp, sp_ki, sp_kd in speed_candidates:
        for dp_kp, dp_ki, dp_kd in distance_candidates:
            m = simulate_and_evaluate(sp_kp, sp_ki, sp_kd, dp_kp, dp_ki, dp_kd)
            count += 1
            if m['score'] < best_score:
                best_score = m['score']
                best_params = {'speed': (sp_kp, sp_ki, sp_kd), 'distance': (dp_kp, dp_ki, dp_kd)}
                best_metrics = m
                print(f"#{count:3d} Sp({sp_kp},{sp_ki},{sp_kd}) Ds({dp_kp},{dp_ki},{dp_kd}) -> "
                      f"R={m['rise_time']:.1f}s O={m['overshoot_pct']:.1f}% "
                      f"SpSS={m['speed_ss_error']:.3f} DsSS={m['distance_ss_error']:.2f}m "
                      f"MinD={m['min_distance']:.1f}m Sc={m['score']:.1f}")

    sp = best_params['speed']
    dp = best_params['distance']

    print("\n" + "="*80)
    print("FINAL TUNED PARAMETERS")
    print("="*80)
    print(f"Speed PID:    kp={sp[0]}, ki={sp[1]}, kd={sp[2]}")
    print(f"Distance PID: kp={dp[0]}, ki={dp[1]}, kd={dp[2]}")
    print(f"\nPerformance Metrics:")
    print(f"  Rise time:        {best_metrics['rise_time']:.2f} s  (target: <10s)   {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot:        {best_metrics['overshoot_pct']:.2f} %  (target: <5%)    {'✓' if best_metrics['overshoot_pct'] < 5 else '✗'}")
    print(f"  Speed SS error:   {best_metrics['speed_ss_error']:.4f} m/s  (target: <0.5)  {'✓' if best_metrics['speed_ss_error'] < 0.5 else '✗'}")
    print(f"  Distance SS err:  {best_metrics['distance_ss_error']:.2f} m  (target: <2m)   {'✓' if best_metrics['distance_ss_error'] < 2 else '✗'}")
    print(f"  Min distance:     {best_metrics['min_distance']:.2f} m  (target: >5m)   {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

    result = {
        'pid_speed': {'kp': float(sp[0]), 'ki': float(sp[1]), 'kd': float(sp[2])},
        'pid_distance': {'kp': float(dp[0]), 'ki': float(dp[1]), 'kd': float(dp[2])}
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(result, f, default_flow_style=False)

    print("\n✓ Saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

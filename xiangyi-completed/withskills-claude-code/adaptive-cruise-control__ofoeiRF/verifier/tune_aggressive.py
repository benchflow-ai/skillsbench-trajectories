"""Aggressive PID tuning for better distance tracking."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def simulate_and_evaluate(speed_kp, speed_ki, speed_kd, distance_kp, distance_ki, distance_kd):
    """Simulate and evaluate performance."""
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
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance
        })

    df = pd.DataFrame(results)

    # Metrics
    cruise = df[df['mode'] == 'cruise']
    metrics = {}

    if len(cruise) > 0:
        target_90 = 0.9 * set_speed
        rise_data = cruise[cruise['ego_speed'] >= target_90]
        metrics['rise_time'] = rise_data.iloc[0]['time'] if len(rise_data) > 0 else 999.0
        metrics['overshoot_pct'] = max(0, (cruise['ego_speed'].max() - set_speed) / set_speed * 100)
        steady = cruise[cruise['time'] >= cruise['time'].max() - 5.0]
        metrics['speed_ss_error'] = abs(steady['ego_speed'].mean() - set_speed) if len(steady) > 0 else 999.0
    else:
        metrics['rise_time'] = metrics['overshoot_pct'] = metrics['speed_ss_error'] = 999.0

    follow = df[(df['mode'] == 'follow') & (df['distance_error'].notna())]
    if len(follow) > 30:
        # Use last 30% for steady state
        steady_follow = follow.iloc[int(0.7 * len(follow)):]
        metrics['distance_ss_error'] = abs(steady_follow['distance_error'].mean())
        metrics['min_distance'] = follow['distance'].min()

        # Check max absolute distance error in follow mode
        metrics['max_dist_error'] = follow['distance_error'].abs().max()
    else:
        metrics['distance_ss_error'] = 0.0
        metrics['min_distance'] = 999.0
        metrics['max_dist_error'] = 0.0

    # Scoring - heavily penalize constraint violations
    score = 0.0

    # Hard constraints with heavy penalties
    if metrics['rise_time'] > 10.0:
        score += (metrics['rise_time'] - 10.0) * 100.0
    if metrics['overshoot_pct'] > 5.0:
        score += (metrics['overshoot_pct'] - 5.0) * 50.0
    if metrics['speed_ss_error'] > 0.5:
        score += (metrics['speed_ss_error'] - 0.5) * 200.0
    if metrics['distance_ss_error'] > 2.0:
        score += (metrics['distance_ss_error'] - 2.0) * 100.0
    if metrics['min_distance'] < 5.0:
        score += (5.0 - metrics['min_distance']) * 500.0

    # Optimization objectives
    score += metrics['rise_time'] * 0.5
    score += metrics['overshoot_pct'] * 1.0
    score += metrics['speed_ss_error'] * 20.0
    score += metrics['distance_ss_error'] * 30.0

    metrics['score'] = score
    return metrics


def main():
    """Run aggressive tuning."""
    print("Aggressive PID Tuning\n" + "="*50)

    # Speed PID - focus on meeting constraints
    speed_params = [(2.0, 0.01, 0.1), (2.5, 0.01, 0.1), (3.0, 0.01, 0.0), (3.5, 0.01, 0.0), (4.0, 0.0, 0.0)]

    # Distance PID - try higher gains with integral
    dist_params = [
        (0.5, 0.01, 0.5), (0.8, 0.02, 0.5), (1.0, 0.02, 0.5),
        (1.2, 0.02, 0.5), (1.5, 0.02, 0.5), (2.0, 0.02, 0.5),
        (0.5, 0.05, 1.0), (0.8, 0.05, 1.0), (1.0, 0.05, 1.0),
        (1.5, 0.05, 1.0), (2.0, 0.05, 1.0),
        (0.8, 0.01, 0.0), (1.0, 0.01, 0.0), (1.5, 0.01, 0.0)
    ]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    print("\nTesting combinations...")
    for sp_kp, sp_ki, sp_kd in speed_params:
        for dp_kp, dp_ki, dp_kd in dist_params:
            m = simulate_and_evaluate(sp_kp, sp_ki, sp_kd, dp_kp, dp_ki, dp_kd)
            if m['score'] < best_score:
                best_score = m['score']
                best_params = {'speed': (sp_kp, sp_ki, sp_kd), 'distance': (dp_kp, dp_ki, dp_kd)}
                best_metrics = m
                print(f"Speed({sp_kp},{sp_ki},{sp_kd}) Dist({dp_kp},{dp_ki},{dp_kd}) -> "
                      f"Rise={m['rise_time']:.1f}s Over={m['overshoot_pct']:.1f}% "
                      f"SpSS={m['speed_ss_error']:.3f} DistSS={m['distance_ss_error']:.2f}m "
                      f"MinD={m['min_distance']:.1f}m Score={m['score']:.1f}")

    sp = best_params['speed']
    dp = best_params['distance']

    print("\n" + "="*80)
    print("BEST PARAMETERS")
    print("="*80)
    print(f"Speed PID:    kp={sp[0]}, ki={sp[1]}, kd={sp[2]}")
    print(f"Distance PID: kp={dp[0]}, ki={dp[1]}, kd={dp[2]}")
    print(f"\nPerformance:")
    print(f"  Rise time:        {best_metrics['rise_time']:.2f} s  (< 10s) {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot:        {best_metrics['overshoot_pct']:.2f} %  (< 5%) {'✓' if best_metrics['overshoot_pct'] < 5 else '✗'}")
    print(f"  Speed SS error:   {best_metrics['speed_ss_error']:.4f} m/s  (< 0.5) {'✓' if best_metrics['speed_ss_error'] < 0.5 else '✗'}")
    print(f"  Distance SS err:  {best_metrics['distance_ss_error']:.2f} m  (< 2m) {'✓' if best_metrics['distance_ss_error'] < 2 else '✗'}")
    print(f"  Min distance:     {best_metrics['min_distance']:.2f} m  (> 5m) {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

    result = {
        'pid_speed': {'kp': float(sp[0]), 'ki': float(sp[1]), 'kd': float(sp[2])},
        'pid_distance': {'kp': float(dp[0]), 'ki': float(dp[1]), 'kd': float(dp[2])}
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(result, f, default_flow_style=False)

    print("\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    main()

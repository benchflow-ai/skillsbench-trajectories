"""Find best PID parameters through systematic testing."""

import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl
import numpy as np


def test_params(speed_kp, speed_ki, speed_kd, dist_kp, dist_ki, dist_kd):
    """Test a set of parameters."""
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor = pd.read_csv('/root/sensor_data.csv')
    dt = 0.1
    set_speed = 30.0

    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
    config['pid_distance'] = {'kp': dist_kp, 'ki': dist_ki, 'kd': dist_kd}

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0

    results = []
    for _, row in sensor.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel * dt
        ego_speed = max(0, ego_speed)

        results.append({
            't': row['time'],
            'v': ego_speed,
            'mode': mode,
            'dist': distance if distance else 999,
            'dist_err': dist_err
        })

    df = pd.DataFrame(results)

    # Metrics
    cruise = df[df['mode'] == 'cruise']
    if len(cruise) < 20:
        return None

    # Rise time
    above_27 = cruise[cruise['v'] >= 27.0]  # 90% of 30
    rise_time = above_27['t'].iloc[0] if len(above_27) > 0 else 999

    # Overshoot
    max_v = cruise['v'].max()
    overshoot = (max_v - set_speed) / set_speed * 100

    # Speed SS
    speed_ss = abs(cruise['v'].iloc[-20:].mean() - set_speed)

    # Distance SS
    follow = df[df['mode'] == 'follow']
    if len(follow) > 20:
        dist_errs = follow['dist_err'].dropna()
        dist_ss = abs(dist_errs.iloc[-20:].mean()) if len(dist_errs) > 0 else 999
    else:
        dist_ss = 999

    # Min distance
    min_dist = df['dist'].min()

    return {
        'rise': rise_time,
        'overshoot': overshoot,
        'speed_ss': speed_ss,
        'dist_ss': dist_ss,
        'min_dist': min_dist
    }


print("Systematic PID Parameter Search")
print("=" * 70)

# Key insight: Add derivative term to speed controller to reduce overshoot
# D term opposes rapid changes in error

best_score = -1000
best_params = None

# Try different combinations
tests = [
    # (speed_kp, speed_ki, speed_kd, dist_kp, dist_ki, dist_kd)
    (0.30, 0.04, 0.3, 8.0, 0.4, 2.5),
    (0.30, 0.04, 0.4, 8.0, 0.4, 2.5),
    (0.30, 0.04, 0.5, 8.0, 0.4, 2.5),
    (0.35, 0.04, 0.3, 8.0, 0.4, 2.5),
    (0.35, 0.04, 0.4, 8.0, 0.4, 2.5),
    (0.35, 0.04, 0.5, 8.0, 0.4, 2.5),
    (0.35, 0.04, 0.6, 8.0, 0.4, 2.5),
    (0.40, 0.04, 0.4, 8.0, 0.4, 2.5),
    (0.40, 0.04, 0.5, 8.0, 0.4, 2.5),
    (0.40, 0.04, 0.6, 8.0, 0.4, 2.5),
    # Try even higher distance gains
    (0.35, 0.04, 0.5, 9.0, 0.4, 2.5),
    (0.35, 0.04, 0.5, 9.0, 0.5, 2.5),
    (0.35, 0.04, 0.5, 9.0, 0.5, 3.0),
]

for params in tests:
    metrics = test_params(*params)
    if metrics is None:
        continue

    # Score based on requirements
    score = 0
    if metrics['rise'] < 10:
        score += 10
    if metrics['overshoot'] < 5:
        score += 30
    if metrics['speed_ss'] < 0.5:
        score += 10
    if metrics['dist_ss'] < 2.0:
        score += 20
    if metrics['min_dist'] > 5:
        score += 30

    # Penalty for violations
    if metrics['overshoot'] >= 5:
        score -= (metrics['overshoot'] - 5) * 2
    if metrics['min_dist'] < 5:
        score -= (5 - metrics['min_dist']) * 10

    print(f"\nParams: speed({params[0]}, {params[1]}, {params[2]}), dist({params[3]}, {params[4]}, {params[5]})")
    print(f"  Rise:{metrics['rise']:5.1f}s, OS:{metrics['overshoot']:5.1f}%, " +
          f"SS_v:{metrics['speed_ss']:.3f}, SS_d:{metrics['dist_ss']:5.2f}, " +
          f"min_d:{metrics['min_dist']:5.2f}m | score:{score:4.0f}")

    if score > best_score:
        best_score = score
        best_params = params
        best_metrics = metrics

print("\n" + "=" * 70)
print("BEST PARAMETERS")
print("=" * 70)
print(f"\nSpeed:    kp={best_params[0]}, ki={best_params[1]}, kd={best_params[2]}")
print(f"Distance: kp={best_params[3]}, ki={best_params[4]}, kd={best_params[5]}")
print(f"\nMetrics:")
print(f"  Rise time:        {best_metrics['rise']:6.2f}s  ({'✓' if best_metrics['rise'] < 10 else '✗'})")
print(f"  Overshoot:        {best_metrics['overshoot']:6.2f}%  ({'✓' if best_metrics['overshoot'] < 5 else '✗'})")
print(f"  Speed SS error:   {best_metrics['speed_ss']:6.3f} m/s ({'✓' if best_metrics['speed_ss'] < 0.5 else '✗'})")
print(f"  Distance SS error:{best_metrics['dist_ss']:6.3f} m   ({'✓' if best_metrics['dist_ss'] < 2 else '✗'})")
print(f"  Min distance:     {best_metrics['min_dist']:6.2f} m   ({'✓' if best_metrics['min_dist'] > 5 else '✗'})")

# Save
result = {
    'pid_speed': {
        'kp': float(best_params[0]),
        'ki': float(best_params[1]),
        'kd': float(best_params[2])
    },
    'pid_distance': {
        'kp': float(best_params[3]),
        'ki': float(best_params[4]),
        'kd': float(best_params[5])
    }
}

with open('/root/tuning_results.yaml', 'w') as f:
    yaml.dump(result, f, default_flow_style=False)

print("\n✓ Saved to tuning_results.yaml")

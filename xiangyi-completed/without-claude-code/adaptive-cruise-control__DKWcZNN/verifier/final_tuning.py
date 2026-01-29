"""Final comprehensive PID tuning with improved ACC system."""

import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def run_simulation(speed_kp, speed_ki, speed_kd, dist_kp, dist_ki, dist_kd):
    """Run full simulation and return metrics."""
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

    # Calculate metrics
    cruise = df[df['mode'] == 'cruise']
    if len(cruise) < 20:
        return None

    # 1. Rise time (90% of setpoint)
    above_27 = cruise[cruise['v'] >= 27.0]
    rise_time = above_27['t'].iloc[0] if len(above_27) > 0 else 999

    # 2. Overshoot
    max_v = cruise['v'].max()
    overshoot = (max_v - set_speed) / set_speed * 100

    # 3. Speed steady-state error (last 10%)
    n_steady = max(int(len(cruise) * 0.1), 10)
    speed_ss = abs(cruise['v'].iloc[-n_steady:].mean() - set_speed)

    # 4. Distance steady-state error (last 10% of follow mode)
    follow = df[df['mode'] == 'follow']
    if len(follow) > 20:
        dist_errs = follow['dist_err'].dropna()
        if len(dist_errs) > 20:
            n_steady = max(int(len(dist_errs) * 0.1), 10)
            dist_ss = abs(dist_errs.iloc[-n_steady:].mean())
        else:
            dist_ss = 999
    else:
        dist_ss = 999

    # 5. Minimum distance
    min_dist = df['dist'].min()

    return {
        'rise': rise_time,
        'overshoot': overshoot,
        'speed_ss': speed_ss,
        'dist_ss': dist_ss,
        'min_dist': min_dist,
        'params': (speed_kp, speed_ki, speed_kd, dist_kp, dist_ki, dist_kd)
    }


print("Final Comprehensive PID Tuning")
print("=" * 75)
print("\nKey Insights:")
print("- Low speed_kp + moderate speed_kd reduces overshoot via damping")
print("- Higher dist_kp + dist_kd provides quick response to prevent collision")
print("- Controller reset on mode change prevents integral windup")
print("-" * 75)

# Carefully chosen parameter sets based on control theory
# Format: (speed_kp, speed_ki, speed_kd, dist_kp, dist_ki, dist_kd)
test_sets = [
    # Conservative speed, aggressive distance
    (0.5, 0.045, 0.7, 9.0, 0.5, 3.0),
    (0.5, 0.045, 0.8, 9.0, 0.5, 3.0),
    (0.5, 0.045, 0.9, 9.0, 0.5, 3.0),
    (0.5, 0.050, 0.7, 9.0, 0.5, 3.0),
    (0.5, 0.050, 0.8, 9.0, 0.5, 3.0),

    # Try even more aggressive distance control
    (0.5, 0.045, 0.8, 9.5, 0.5, 3.5),
    (0.5, 0.045, 0.8, 9.5, 0.6, 3.5),
    (0.5, 0.050, 0.8, 9.5, 0.6, 3.5),
]

best = None
best_score = -10000
passing = []

print(f"\nTesting {len(test_sets)} parameter combinations...\n")

for i, params in enumerate(test_sets, 1):
    result = run_simulation(*params)
    if result is None:
        continue

    # Count passing requirements
    passes = sum([
        result['rise'] < 10,
        result['overshoot'] < 5,
        result['speed_ss'] < 0.5,
        result['dist_ss'] < 2.0,
        result['min_dist'] > 5.0
    ])

    # Scoring function
    score = passes * 100

    # Penalties for violations
    if result['overshoot'] >= 5:
        score -= (result['overshoot'] - 5) * 5
    if result['min_dist'] < 5:
        score -= (5 - result['min_dist']) * 30
    if result['dist_ss'] >= 2:
        score -= (result['dist_ss'] - 2) * 3

    # Bonuses for good performance
    if result['overshoot'] < 5:
        score += (5 - result['overshoot']) * 2
    if result['min_dist'] > 5:
        score += (result['min_dist'] - 5) * 5

    status = "✓✓✓" if passes == 5 else f"{passes}/5"

    print(f"[{i:2d}] speed({params[0]},{params[1]},{params[2]}) " +
          f"dist({params[3]},{params[4]},{params[5]})")
    print(f"     RT:{result['rise']:5.2f}s OS:{result['overshoot']:5.2f}% " +
          f"SS_v:{result['speed_ss']:.3f} SS_d:{result['dist_ss']:5.2f} " +
          f"min_d:{result['min_dist']:5.2f}m | {status} score:{score:.0f}")

    if passes == 5:
        passing.append(result)

    if score > best_score:
        best_score = score
        best = result

print("\n" + "=" * 75)
if len(passing) > 0:
    print(f"SUCCESS! Found {len(passing)} solution(s) meeting all requirements")
    print("=" * 75)
    best = passing[0]  # Use first passing solution
else:
    print("No perfect solution found. Using best candidate.")
    print("=" * 75)

p = best['params']
m = best
print(f"\nBest Parameters:")
print(f"  Speed PID:    kp={p[0]}, ki={p[1]}, kd={p[2]}")
print(f"  Distance PID: kp={p[3]}, ki={p[4]}, kd={p[5]}")

print(f"\nPerformance:")
checks = [
    ("Rise time < 10s", m['rise'], 10, lambda x: x < 10),
    ("Overshoot < 5%", m['overshoot'], 5, lambda x: x < 5),
    ("Speed SS < 0.5 m/s", m['speed_ss'], 0.5, lambda x: x < 0.5),
    ("Distance SS < 2m", m['dist_ss'], 2.0, lambda x: x < 2.0),
    ("Min distance > 5m", m['min_dist'], 5.0, lambda x: x > 5.0),
]

for name, val, target, check in checks:
    status = "✓" if check(val) else "✗"
    print(f"  {name:25s} {val:7.3f} (target: {str(target):6s}) {status}")

# Save results
tuning_results = {
    'pid_speed': {
        'kp': float(p[0]),
        'ki': float(p[1]),
        'kd': float(p[2])
    },
    'pid_distance': {
        'kp': float(p[3]),
        'ki': float(p[4]),
        'kd': float(p[5])
    }
}

with open('/root/tuning_results.yaml', 'w') as f:
    yaml.dump(tuning_results, f, default_flow_style=False)

print("\n✓ Saved to tuning_results.yaml")

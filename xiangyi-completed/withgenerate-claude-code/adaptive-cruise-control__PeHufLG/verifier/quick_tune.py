"""Quick PID tuning with focused parameter search."""

import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def simulate_with_params(kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist):
    """Run simulation with given PID parameters."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['pid_speed'] = {'kp': kp_speed, 'ki': ki_speed, 'kd': kd_speed}
    config['pid_distance'] = {'kp': kp_dist, 'ki': ki_dist, 'kd': kd_dist}

    sensor_df = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    ego_speed = 0.0
    results = []

    for idx, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'mode': mode,
            'distance_error': distance_error
        })

        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)

    return pd.DataFrame(results)


def calculate_metrics(results_df):
    """Calculate performance metrics."""
    set_speed = 30.0
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    # Rise time
    if len(cruise_data) > 0:
        target = 0.9 * set_speed
        rise_data = cruise_data[cruise_data['ego_speed'] >= target]
        rise_time = rise_data.iloc[0]['time'] if len(rise_data) > 0 else 999.0

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot = (max_speed - set_speed) / set_speed * 100 if max_speed > set_speed else 0.0

        # Steady-state error
        steady_start = int(len(cruise_data) * 0.8)
        if steady_start < len(cruise_data):
            sse = abs(cruise_data.iloc[steady_start:]['ego_speed'].mean() - set_speed)
        else:
            sse = abs(cruise_data.iloc[-1]['ego_speed'] - set_speed)
    else:
        rise_time, overshoot, sse = 999.0, 0.0, 999.0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'steady_state_error': sse
    }


# Hand-tuned candidates focusing on meeting requirements
candidates = [
    # (kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
    (2.0, 0.1, 2.0, 1.5, 0.05, 2.0),   # Balanced with damping
    (2.5, 0.1, 2.5, 2.0, 0.05, 2.5),   # More aggressive
    (1.5, 0.15, 2.0, 1.0, 0.08, 2.0),  # Conservative
    (2.0, 0.1, 3.0, 1.5, 0.05, 3.0),   # High damping
    (2.5, 0.15, 2.0, 2.0, 0.08, 2.0),  # Balanced integral
    (1.8, 0.1, 2.5, 1.5, 0.05, 2.5),   # Medium response
    (2.2, 0.12, 2.2, 1.8, 0.06, 2.2),  # Symmetric
]

print("Testing candidate parameter sets...")
best_params = None
best_metrics = None

for i, (kp_s, ki_s, kd_s, kp_d, ki_d, kd_d) in enumerate(candidates):
    print(f"\nCandidate {i+1}: Speed=({kp_s}, {ki_s}, {kd_s}), Dist=({kp_d}, {ki_d}, {kd_d})")

    results = simulate_with_params(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
    metrics = calculate_metrics(results)

    print(f"  Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {metrics['overshoot']:.2f}% (target: <5%)")
    print(f"  SS Error:  {metrics['steady_state_error']:.3f} m/s (target: <0.5)")

    # Check if all requirements met
    if (metrics['rise_time'] < 10 and
        metrics['overshoot'] < 5 and
        metrics['steady_state_error'] < 0.5):
        print("  ✓ All requirements met!")
        if best_params is None:
            best_params = (kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
            best_metrics = metrics
    else:
        print("  ✗ Requirements not met")

# Use best candidate or fallback
if best_params is None:
    print("\nNo candidate met all requirements. Using best compromise.")
    best_params = (2.0, 0.1, 2.5, 1.5, 0.05, 2.5)
else:
    print(f"\nBest parameters found!")

kp_s, ki_s, kd_s, kp_d, ki_d, kd_d = best_params

# Save tuned parameters
tuned = {
    'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
    'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
}

with open('tuning_results.yaml', 'w') as f:
    yaml.dump(tuned, f, default_flow_style=False)

print(f"\nFinal parameters saved to tuning_results.yaml")
print(f"Speed PID:    Kp={kp_s}, Ki={ki_s}, Kd={kd_s}")
print(f"Distance PID: Kp={kp_d}, Ki={ki_d}, Kd={kd_d}")

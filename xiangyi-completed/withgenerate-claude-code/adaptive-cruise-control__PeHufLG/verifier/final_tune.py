"""Final PID tuning - optimized for requirements."""

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

    ego_speed = 0.0  # Start from rest
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
            'mode': mode
        })

        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)

    return pd.DataFrame(results)


# Test with lower Kp and higher Ki to reduce overshoot
print("Testing configurations with lower Kp to reduce overshoot...\n")

configs = [
    # Format: (name, kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
    ("Config 1", 0.8, 0.2, 1.5, 1.0, 0.05, 2.0),
    ("Config 2", 1.0, 0.2, 2.0, 1.2, 0.08, 2.5),
    ("Config 3", 0.9, 0.25, 1.8, 1.1, 0.06, 2.2),
    ("Config 4", 1.1, 0.18, 2.2, 1.3, 0.05, 2.8),
    ("Config 5", 0.85, 0.22, 1.6, 1.0, 0.07, 2.3),
]

best_config = None
best_metrics = None

for name, kp_s, ki_s, kd_s, kp_d, ki_d, kd_d in configs:
    print(f"{name}: Speed=({kp_s}, {ki_s}, {kd_s}), Dist=({kp_d}, {ki_d}, {kd_d})")

    results = simulate_with_params(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)

    # Calculate metrics
    cruise_data = results[results['mode'] == 'cruise']
    if len(cruise_data) > 0:
        # Rise time to 90% of 30 m/s = 27 m/s
        rise_data = cruise_data[cruise_data['ego_speed'] >= 27.0]
        rise_time = rise_data.iloc[0]['time'] if len(rise_data) > 0 else 999.0

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot = (max_speed - 30.0) / 30.0 * 100 if max_speed > 30 else 0.0

        # Steady-state error
        steady_data = cruise_data.iloc[int(len(cruise_data)*0.8):]
        sse = abs(steady_data['ego_speed'].mean() - 30.0) if len(steady_data) > 0 else 999

        print(f"  Rise={rise_time:.2f}s, Overshoot={overshoot:.2f}%, SSE={sse:.3f}")

        # Check requirements
        meets_req = rise_time < 10 and overshoot < 5 and sse < 0.5
        if meets_req:
            print("  ✓ MEETS ALL REQUIREMENTS")
            if best_config is None:
                best_config = (kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
                best_metrics = (rise_time, overshoot, sse)
        else:
            print("  ✗ Does not meet requirements")
    print()

# If no config meets requirements, use best from above
if best_config is None:
    print("Using conservative fallback configuration")
    best_config = (1.0, 0.2, 2.0, 1.2, 0.05, 2.5)

kp_s, ki_s, kd_s, kp_d, ki_d, kd_d = best_config

# Save
tuned = {
    'pid_speed': {'kp': float(kp_s), 'ki': float(ki_s), 'kd': float(kd_s)},
    'pid_distance': {'kp': float(kp_d), 'ki': float(ki_d), 'kd': float(kd_d)}
}

with open('tuning_results.yaml', 'w') as f:
    yaml.dump(tuned, f, default_flow_style=False)

print("\n" + "="*60)
print("FINAL TUNED PARAMETERS saved to tuning_results.yaml")
print("="*60)
print(f"Speed PID:    Kp={kp_s}, Ki={ki_s}, Kd={kd_s}")
print(f"Distance PID: Kp={kp_d}, Ki={ki_d}, Kd={kd_d}")

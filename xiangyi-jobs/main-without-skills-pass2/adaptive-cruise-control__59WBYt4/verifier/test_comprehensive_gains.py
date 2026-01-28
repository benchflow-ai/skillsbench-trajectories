"""Comprehensive test of PID gain combinations."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

def test_gains(speed_gains, distance_gains):
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    sensor_data = pd.read_csv('/root/sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    prev_lead_speed = None
    min_distance = float('inf')

    follow_errors = []

    for _, row in sensor_data.iterrows():
        time = row['time']
        lead_speed_csv = row['lead_speed'] if pd.notna(row['lead_speed']) else None

        if lead_speed_csv is not None:
            if prev_lead_speed is None:
                lead_position = ego_position + row['distance']
            else:
                lead_position += prev_lead_speed * dt

            distance = lead_position - ego_position
            lead_speed = lead_speed_csv
            prev_lead_speed = lead_speed_csv
        else:
            distance = None
            lead_speed = None
            lead_position = None
            prev_lead_speed = None

        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_position += ego_speed * dt

        if distance is not None:
            min_distance = min(min_distance, distance)

        if mode == 'follow' and distance_error is not None and time >= 120.0:
            follow_errors.append(abs(distance_error))

    avg_error = sum(follow_errors) / len(follow_errors) if follow_errors else 999

    # Score: must have min_dist > 5, then minimize avg_error
    if min_distance < 5.0:
        score = 10000 + (5.0 - min_distance) * 100
    else:
        score = avg_error

    return min_distance, avg_error, score

# Test combinations
speed_gains = (1.0, 0.0, 0.0)

distance_test_cases = [
    (0.45, 0.004, 1.4),
    (0.48, 0.005, 1.45),
    (0.50, 0.005, 1.5),
    (0.52, 0.005, 1.55),
    (0.50, 0.006, 1.5),
    (0.50, 0.007, 1.5),
    (0.50, 0.008, 1.5),
    (0.55, 0.006, 1.6),
    (0.55, 0.007, 1.6),
]

print("Testing distance controller gains (speed = 1.0, 0.0, 0.0):")
print("Kp,  Ki,   Kd  | Min Dist | Avg Err | Score")
print("-" * 55)

best_score = float('inf')
best_gains = None

for gains in distance_test_cases:
    min_d, avg_e, score = test_gains(speed_gains, gains)
    marker = " <--" if score < best_score else ""
    if score < best_score:
        best_score = score
        best_gains = gains
    print(f"{gains[0]:.1f}, {gains[1]:.3f}, {gains[2]:.1f} | {min_d:8.2f} | {avg_e:7.2f} | {score:7.2f}{marker}")

print(f"\nBest: Kp={best_gains[0]:.1f}, Ki={best_gains[1]:.3f}, Kd={best_gains[2]:.1f}")

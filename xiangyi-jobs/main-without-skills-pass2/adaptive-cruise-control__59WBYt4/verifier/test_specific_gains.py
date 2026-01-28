"""Test specific PID gain combinations."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

def test_gains(speed_gains, distance_gains):
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Update with test gains
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')

    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Simulation with position tracking
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

        if mode == 'follow' and distance_error is not None and time >= 100.0:
            follow_errors.append(abs(distance_error))

    avg_error = sum(follow_errors) / len(follow_errors) if follow_errors else 999

    return min_distance, avg_error

# Test different combinations
speed_gains = (1.0, 0.0, 0.0)

test_cases = [
    (1.0, 0.02, 2.5),
    (2.0, 0.05, 2.0),
    (3.0, 0.1, 2.0),
    (4.0, 0.2, 2.5),
    (5.0, 0.3, 3.0),
]

print("Testing distance controller gains:")
print("Kp,  Ki,   Kd  | Min Dist | Avg Dist Err")
print("-" * 50)

for gains in test_cases:
    min_d, avg_e = test_gains(speed_gains, gains)
    print(f"{gains[0]:.1f}, {gains[1]:.2f}, {gains[2]:.1f} | {min_d:8.2f} | {avg_e:12.2f}")

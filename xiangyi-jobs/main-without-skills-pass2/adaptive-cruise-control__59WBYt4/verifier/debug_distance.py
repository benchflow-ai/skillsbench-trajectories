"""Debug distance control."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

# Load configuration
with open('/root/vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Update with current best gains
config['pid_speed'] = {'kp': 1.0, 'ki': 0.0, 'kd': 0.0}
config['pid_distance'] = {'kp': 0.3, 'ki': 0.02, 'kd': 0.1}

# Load sensor data
sensor_data = pd.read_csv('/root/sensor_data.csv')

# Initialize ACC
acc = AdaptiveCruiseControl(config)
dt = config['simulation']['dt']

# Run simulation
ego_speed = 0.0
min_dist = float('inf')

follow_data = []

for i, row in sensor_data.iterrows():
    time = row['time']
    lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
    distance = row['distance'] if pd.notna(row['distance']) else None

    acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

    # Update ego speed
    ego_speed += acceleration_cmd * dt
    ego_speed = max(0.0, ego_speed)

    if distance is not None:
        min_dist = min(min_dist, distance)

    if mode == 'follow' and distance_error is not None:
        follow_data.append({
            'time': time,
            'distance_error': distance_error,
            'distance': distance,
            'ego_speed': ego_speed,
            'lead_speed': lead_speed
        })

print(f"Min distance: {min_dist:.2f}m")
print(f"\nFollow mode data points: {len(follow_data)}")

if follow_data:
    # Last 30 seconds
    last_30s = [d for d in follow_data if d['time'] >= follow_data[-1]['time'] - 30.0]
    print(f"Last 30s data points: {len(last_30s)}")

    if last_30s:
        avg_dist_error = sum(abs(d['distance_error']) for d in last_30s) / len(last_30s)
        print(f"Average absolute distance error (last 30s): {avg_dist_error:.2f}m")

        # Show sample
        print("\nSample from last 30s:")
        for d in last_30s[-10:]:
            desired_dist = 10 + 1.5 * d['ego_speed']
            print(f"t={d['time']:.1f}: dist={d['distance']:.2f}, desired={desired_dist:.2f}, "
                  f"error={d['distance_error']:.2f}, ego={d['ego_speed']:.2f}, lead={d['lead_speed']:.2f}")

"""Quick test to debug ACC behavior."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

# Load configuration
with open('/root/vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Update with tuned gains
config['pid_speed'] = {'kp': 1.0, 'ki': 0.0, 'kd': 0.0}
config['pid_distance'] = {'kp': 1.5, 'ki': 0.02, 'kd': 0.5}

# Load sensor data
sensor_data = pd.read_csv('/root/sensor_data.csv')

# Initialize ACC
acc = AdaptiveCruiseControl(config)
dt = config['simulation']['dt']

# Run simulation
ego_speed = 0.0

print("Time, EgoSpeed, LeadSpeed, Distance, Accel, Mode, DistErr")
for i, row in sensor_data.iterrows():
    if i > 350:  # Just check around when lead vehicle appears
        break

    time = row['time']
    lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
    distance = row['distance'] if pd.notna(row['distance']) else None

    acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

    # Update ego speed
    ego_speed += acceleration_cmd * dt
    ego_speed = max(0.0, ego_speed)

    if i >= 295 and i <= 310:
        dist_err_str = f"{distance_error:.2f}" if distance_error is not None else "None"
        lead_spd_str = f"{lead_speed:.2f}" if lead_speed is not None else "None"
        dist_str = f"{distance:.2f}" if distance is not None else "None"
        print(f"{time:.1f}, {ego_speed:.2f}, {lead_spd_str}, {dist_str}, {acceleration_cmd:.2f}, {mode}, {dist_err_str}")

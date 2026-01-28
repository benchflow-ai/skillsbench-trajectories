"""Debug simulation at specific time"""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

# Load configs
with open('vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

with open('tuning_results.yaml', 'r') as f:
    tuned_gains = yaml.safe_load(f)

config['pid_speed'] = tuned_gains['pid_speed']
config['pid_distance'] = tuned_gains['pid_distance']

sensor_data = pd.read_csv('sensor_data.csv')
acc = AdaptiveCruiseControl(config)
dt = 0.1

# Simulate to t=30s
ego_speed = 0.0
for idx, row in sensor_data.iterrows():
    time = row['time']
    lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
    distance = row['distance'] if pd.notna(row['distance']) else None

    accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

    if time >= 29.0 and time <= 31.0:
        print(f"t={time:.1f}: ego_speed={ego_speed:.2f}, lead_speed={lead_speed}, distance={distance}")
        print(f"  mode={mode}, accel={accel_cmd:.2f}, dist_error={dist_error}")
        if mode == 'follow':
            desired = config['acc_settings']['min_distance'] + config['acc_settings']['time_headway'] * ego_speed
            print(f"  desired_distance={desired:.2f}m")

    ego_speed += accel_cmd * dt
    ego_speed = max(0, ego_speed)

    if time > 31:
        break

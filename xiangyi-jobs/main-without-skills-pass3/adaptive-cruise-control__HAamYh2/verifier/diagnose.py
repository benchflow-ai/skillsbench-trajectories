"""Diagnostic script to understand distance tracking issue"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

# Load configuration
with open('tuning_results.yaml', 'r') as f:
    tuned_gains = yaml.safe_load(f)

with open('vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Update with tuned gains
config['pid_speed'] = tuned_gains['pid_speed']
config['pid_distance'] = tuned_gains['pid_distance']

# Load sensor data
sensor_data = pd.read_csv('sensor_data.csv')

# Run simulation
acc = AdaptiveCruiseControl(config)
dt = config['simulation']['dt']

ego_speed = 0.0

print("Simulating and analyzing follow mode...")
print("=" * 80)

for idx, row in sensor_data.iterrows():
    time = row['time']
    lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
    distance = row['distance'] if pd.notna(row['distance']) else None

    accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
    ego_speed = max(0.0, ego_speed + accel_cmd * dt)

    # Print detailed info when lead vehicle first appears
    if 30.0 <= time <= 35.0 and lead_speed is not None:
        desired_dist = config['acc_settings']['min_distance'] + config['acc_settings']['time_headway'] * ego_speed
        print(f"t={time:.1f}s: ego_v={ego_speed:.2f}, lead_v={lead_speed:.2f}, dist={distance:.2f}, "
              f"desired={desired_dist:.2f}, error={dist_error:.2f}, accel={accel_cmd:.2f}, mode={mode}")

    # Print info at end of simulation
    if 145.0 <= time <= 150.0 and lead_speed is not None:
        desired_dist = config['acc_settings']['min_distance'] + config['acc_settings']['time_headway'] * ego_speed
        if time == 145.0:
            print("\n" + "=" * 80)
            print("End of simulation (t=145-150s):")
        print(f"t={time:.1f}s: ego_v={ego_speed:.2f}, lead_v={lead_speed:.2f}, dist={distance:.2f}, "
              f"desired={desired_dist:.2f}, error={dist_error:.2f if dist_error else 'N/A'}")

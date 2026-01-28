"""Proper ACC simulation with position tracking."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

# Load configuration
with open('/root/vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Update with tuned gains
config['pid_speed'] = {'kp': 1.0, 'ki': 0.0, 'kd': 0.0}
config['pid_distance'] = {'kp': 1.0, 'ki': 0.02, 'kd': 0.2}

# Load sensor data
sensor_data = pd.read_csv('/root/sensor_data.csv')

# Initialize ACC
acc = AdaptiveCruiseControl(config)
dt = config['simulation']['dt']

# Simulation variables
ego_speed = 0.0
ego_position = 0.0
lead_position = None
prev_lead_speed = None

min_distance = float('inf')
results = []

for i, row in sensor_data.iterrows():
    time = row['time']
    lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None

    # Handle lead vehicle appearance/disappearance
    if lead_speed is not None:
        if prev_lead_speed is None:
            # Lead vehicle just appeared - use initial distance from CSV
            initial_distance = row['distance']
            lead_position = ego_position + initial_distance
        else:
            # Update lead position based on its speed
            lead_position += prev_lead_speed * dt

        # Compute distance
        distance = lead_position - ego_position
        prev_lead_speed = lead_speed
    else:
        distance = None
        lead_position = None
        prev_lead_speed = None

    # Compute control
    acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

    # Update ego vehicle
    ego_speed += acceleration_cmd * dt
    ego_speed = max(0.0, ego_speed)
    ego_position += ego_speed * dt

    # Track minimum distance
    if distance is not None:
        min_distance = min(min_distance, distance)

    # Store results
    results.append({
        'time': time,
        'ego_speed': ego_speed,
        'acceleration_cmd': acceleration_cmd,
        'mode': mode,
        'distance_error': distance_error,
        'distance': distance
    })

# Analyze results
results_df = pd.DataFrame(results)

# Speed metrics
cruise_data = results_df[results_df['mode'] == 'cruise']
print(f"Cruise phase: {len(cruise_data)} timesteps")

if len(cruise_data) > 0:
    speed_90 = 0.9 * 30.0
    rise_time_data = cruise_data[cruise_data['ego_speed'] >= speed_90]
    if len(rise_time_data) > 0:
        rise_time = rise_time_data.iloc[0]['time']
        print(f"Rise time (to 90%): {rise_time:.2f}s")

    max_speed = cruise_data['ego_speed'].max()
    overshoot = max(0, max_speed - 30.0)
    print(f"Max overshoot: {overshoot:.2f} m/s ({overshoot/30*100:.2f}%)")

    ss_data = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 5.0]
    if len(ss_data) > 0:
        ss_error = abs(ss_data['ego_speed'].mean() - 30.0)
        print(f"Speed SS error: {ss_error:.3f} m/s")

# Distance metrics
follow_data = results_df[(results_df['mode'] == 'follow') & results_df['distance_error'].notna()]
print(f"\nFollow phase: {len(follow_data)} timesteps")

if len(follow_data) > 0:
    ss_follow = follow_data[follow_data['time'] >= follow_data['time'].max() - 30.0]
    if len(ss_follow) > 0:
        dist_ss_error = abs(ss_follow['distance_error'].mean())
        print(f"Distance SS error: {dist_ss_error:.2f} m")

print(f"\nMin distance: {min_distance:.2f} m")

# Show sample from follow phase
print("\nSample from last 10 timesteps of follow:")
for _, row in follow_data.tail(10).iterrows():
    if row['distance_error'] is not None:
        desired = 10 + 1.5 * row['ego_speed']
        print(f"t={row['time']:.1f}: dist={row['distance']:.2f}, desired={desired:.2f}, error={row['distance_error']:.2f}")

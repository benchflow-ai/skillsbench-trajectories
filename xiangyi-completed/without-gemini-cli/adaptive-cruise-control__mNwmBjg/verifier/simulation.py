import yaml
import csv
import sys
from acc_system import AdaptiveCruiseControl

# Load config
with open('vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Load tuning results
with open('tuning_results.yaml', 'r') as f:
    tuning = yaml.safe_load(f)

# Update config with tuned gains
# Note: config structure in yaml matches what ACC expects?
# vehicle_params.yaml has 'pid_speed' and 'pid_distance' keys.
# tuning_results.yaml has same keys.
config['pid_speed'].update(tuning['pid_speed'])
config['pid_distance'].update(tuning['pid_distance'])

# Initialize ACC
acc = AdaptiveCruiseControl(config)
dt = config['simulation']['dt']

# Read sensor data
sensor_data = []
with open('sensor_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sensor_data.append(row)

# Simulation state
ego_speed = 0.0 # Initial speed
current_time = 0.0
results = []

# Loop through data
# We expect 1501 rows in sensor_data matching 0.0 to 150.0
for i, row in enumerate(sensor_data):
    # Parse inputs
    # Time from CSV or index? index * dt should match row['time']
    sim_time = i * dt
    
    # Lead data
    lead_speed_str = row['lead_speed']
    dist_str = row['distance']
    
    lead_speed = float(lead_speed_str) if lead_speed_str and lead_speed_str.strip() else None
    distance = float(dist_str) if dist_str and dist_str.strip() else None
    
    # Compute Control
    accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
    
    # Calculate TTC for reporting
    ttc = ''
    if lead_speed is not None and distance is not None:
        rel_speed = ego_speed - lead_speed
        if rel_speed > 0.001:
            val = distance / rel_speed
            ttc = f"{val:.2f}"
            
    # Record result (Current State + Command calculated)
    # distance_error is returned by compute.
    # dist_str is the input distance.
    # We write data matching the prompt format.
    # time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
    
    # Format floats
    # ego_speed is the speed at the START of the interval (state)
    # accel_cmd is the command for THIS interval
    
    res = {
        'time': f"{sim_time:.1f}",
        'ego_speed': f"{ego_speed:.1f}",
        'acceleration_cmd': f"{accel_cmd:.1f}",
        'mode': mode,
        'distance_error': f"{dist_error:.1f}" if mode != 'cruise' else '',
        'distance': f"{distance:.1f}" if distance is not None else '',
        'ttc': ttc
    }
    results.append(res)
    
    # Update Physics for next step
    ego_speed += accel_cmd * dt
    if ego_speed < 0: ego_speed = 0.0

# Write results
headers = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
with open('simulation_results.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(results)

print(f"Simulation complete. {len(results)} rows written.")

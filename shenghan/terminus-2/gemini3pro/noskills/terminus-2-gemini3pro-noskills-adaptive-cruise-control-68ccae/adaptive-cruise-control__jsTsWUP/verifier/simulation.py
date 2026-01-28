import yaml
import csv
import math
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    config.update(tuning)
    return config

def run_simulation():
    config = load_config()
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    ego_speed = 0.0
    
    results = []
    
    # Read sensor data
    sensor_data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_data.append(row)
            
    # Simulation loop
    for i, row in enumerate(sensor_data):
        time = float(row['time'])
        
        # Get sensor inputs (handling missing values)
        lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
        distance = float(row['distance']) if row['distance'] else None
        
        # Compute control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        
        # Update ego vehicle physics
        # v = v + a * dt
        ego_speed += accel_cmd * dt
        if ego_speed < 0: ego_speed = 0
        
        # Calculate TTC for logging
        ttc = None
        if distance is not None and lead_speed is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
        
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error if dist_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })

    # Save results
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)

if __name__ == '__main__':
    run_simulation()

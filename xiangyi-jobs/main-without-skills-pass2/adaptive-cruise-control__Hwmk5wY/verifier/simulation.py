import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    
    # Update config with tuned values
    if 'pid_speed' in tuning:
        config['pid_speed'] = tuning['pid_speed']
    if 'pid_distance' in tuning:
        config['pid_distance'] = tuning['pid_distance']
        
    return config

def load_sensor_data(filepath):
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = {}
            item['time'] = float(row['time'])
            item['ego_speed_orig'] = float(row['ego_speed']) if row['ego_speed'] else 0.0
            item['lead_speed'] = float(row['lead_speed']) if row['lead_speed'] else None
            item['distance_orig'] = float(row['distance']) if row['distance'] else None
            data.append(item)
    return data

def run_simulation():
    config = load_config()
    acc = AdaptiveCruiseControl(config)
    sensor_data = load_sensor_data('sensor_data.csv')
    
    dt = config['simulation']['dt']
    
    # Simulation State
    ego_speed = 0.0 # Initial speed ~0 m/s
    ego_pos = 0.0
    
    lead_pos = None
    
    results = []
    
    for i, step_data in enumerate(sensor_data):
        time = step_data['time']
        
        # Determine Lead Position
        # logic: if lead detected in data:
        #   if first detection (lead_pos is None): spawn relative to current ego
        #   else: integrate lead speed
        
        lead_speed = step_data['lead_speed']
        
        if lead_speed is not None and step_data['distance_orig'] is not None:
            if lead_pos is None:
                # First detection / Spawn
                lead_pos = ego_pos + step_data['distance_orig']
            else:
                # Update position
                lead_pos += lead_speed * dt
        else:
            # Lead lost
            lead_pos = None
            
        # Calculate current simulation distance
        distance = None
        if lead_pos is not None:
            distance = lead_pos - ego_pos
        
        # Run ACC
        # Note: ACC compute should probably use the STATE at time t
        # to calculate command for interval t -> t+dt
        
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        # Calculate TTC for logging
        ttc = None
        if distance is not None and lead_speed is not None:
             rel_speed = ego_speed - lead_speed
             if rel_speed > 0:
                 ttc = distance / rel_speed
        
        # Store Result (State at time t)
        results.append({
            'time': round(time, 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_err, 2) if dist_err is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        })
        
        # Update Physics for next step (t+1)
        ego_speed += accel_cmd * dt
        ego_pos += ego_speed * dt
        
        # Ensure non-negative speed? (Car shouldn't go backwards in this sim usually)
        if ego_speed < 0:
            ego_speed = 0.0

    # Write Results
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

if __name__ == '__main__':
    run_simulation()

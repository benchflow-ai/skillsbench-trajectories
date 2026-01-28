import yaml
import csv
import os
from acc_system import AdaptiveCruiseControl

def run_simulation():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    if os.path.exists('tuning_results.yaml'):
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'] = tuning.get('pid_speed', config['pid_speed'])
            config['pid_distance'] = tuning.get('pid_distance', config['pid_distance'])
    
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    ego_speed = 0.0
    current_distance = None
    results = []
    
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            orig_distance = float(row['distance']) if row['distance'] else None
            
            if lead_speed is not None and current_distance is None:
                # First detection
                current_distance = orig_distance
            elif lead_speed is not None and current_distance is not None:
                # Update distance based on relative speed
                current_distance += (lead_speed - ego_speed) * dt
            else:
                current_distance = None
            
            accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, current_distance, dt)
            
            # Calculate TTC for results
            ttc = None
            if lead_speed is not None and current_distance is not None:
                rel_speed = ego_speed - lead_speed
                if rel_speed > 0:
                    ttc = current_distance / rel_speed
                else:
                    ttc = float('inf')
            
            results.append({
                'time': t,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': dist_err if dist_err is not None else '',
                'distance': current_distance if current_distance is not None else '',
                'ttc': ttc if ttc is not None else ''
            })
            
            # Update ego speed for next step
            ego_speed += accel_cmd * dt
            ego_speed = max(0.0, ego_speed)
            
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)

if __name__ == "__main__":
    run_simulation()
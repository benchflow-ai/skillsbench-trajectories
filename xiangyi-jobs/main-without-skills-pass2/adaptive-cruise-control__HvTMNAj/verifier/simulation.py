import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    
    sensor_data = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    
    acc = AdaptiveCruiseControl(config)
    
    ego_speed = 0.0
    ego_pos = 0.0
    
    results = []
    
    # Reconstruct lead_pos correctly
    # distance = lead_pos - ego_pos_csv
    # lead_pos = distance + ego_pos_csv
    ego_pos_csv = 0.0
    
    for i in range(len(sensor_data)):
        row = sensor_data.iloc[i]
        time = row['time']
        lead_speed = row['lead_speed']
        csv_distance = row['distance']
        csv_ego_speed = row['ego_speed']
        
        # Reconstruct lead_pos from CSV
        if not pd.isna(csv_distance):
            lead_pos = csv_distance + ego_pos_csv
            distance = lead_pos - ego_pos
        else:
            distance = None
            
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        ttc = float('inf')
        if distance is not None and (ego_speed - lead_speed) > 0:
            ttc = distance / (ego_speed - lead_speed)
        
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': distance,
            'ttc': ttc if ttc != float('inf') else None
        })
        
        # Update ego state
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_pos += ego_speed * dt
        
        # Update csv_ego_pos to keep lead_pos reconstruction consistent
        ego_pos_csv += csv_ego_speed * dt
        
    res_df = pd.DataFrame(results)
    res_df.to_csv('simulation_results.csv', index=False)
    print("Simulation complete.")

if __name__ == '__main__':
    run_simulation()

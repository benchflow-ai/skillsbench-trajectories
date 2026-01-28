import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation(vehicle_params_path, tuning_results_path, sensor_data_path, output_path):
    # Load parameters
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)
    
    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)
        
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    
    sensor_df = pd.read_csv(sensor_data_path)
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    ego_speed = 0.0
    ego_pos = 0.0
    
    lead_pos = None
    results = []
    
    for i, row in sensor_df.iterrows():
        t = row['time']
        csv_lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        has_lead = not np.isnan(csv_lead_speed) and not np.isnan(csv_distance)
        
        if has_lead:
            if lead_pos is None:
                # First detection: set lead_pos relative to current ego_pos
                lead_pos = ego_pos + csv_distance
            else:
                # Subsequent steps: move lead vehicle by its speed
                lead_pos += csv_lead_speed * dt
            
            sim_distance = lead_pos - ego_pos
            sim_lead_speed = csv_lead_speed
        else:
            lead_pos = None # Reset if lead vehicle disappears
            sim_distance = None
            sim_lead_speed = None
            
        accel_cmd, mode, dist_err = acc.compute(ego_speed, sim_lead_speed, sim_distance, dt)
        
        ttc = None
        if has_lead:
            rel_speed = ego_speed - sim_lead_speed
            if rel_speed > 0:
                ttc = sim_distance / rel_speed
        
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': sim_distance,
            'ttc': ttc
        })
        
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt

    results_df = pd.DataFrame(results)
    results_df = results_df[['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']]
    results_df.to_csv(output_path, index=False)
    return results_df

if __name__ == "__main__":
    run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv', 'simulation_results.csv')

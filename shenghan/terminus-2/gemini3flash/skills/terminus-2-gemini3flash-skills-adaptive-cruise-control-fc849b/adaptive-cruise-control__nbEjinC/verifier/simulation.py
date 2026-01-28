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
    
    sensor_df = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    results = []
    ego_speed = 0.0
    sim_distance = None
    
    for i, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        if pd.isna(lead_speed):
            lead_speed = None
            sim_distance = None
        else:
            if sim_distance is None:
                sim_distance = csv_distance
            else:
                # Update distance based on relative speed
                # d(t+dt) = d(t) + (v_lead(t) - v_ego(t)) * dt
                # But we use the lead_speed from the CSV
                sim_distance += (lead_speed - ego_speed) * dt

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, sim_distance, dt)
        
        ttc = None
        if lead_speed is not None and sim_distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = sim_distance / rel_speed
        
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': sim_distance,
            'ttc': ttc
        })
        
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False, float_format='%.2f')

if __name__ == '__main__':
    run_simulation()

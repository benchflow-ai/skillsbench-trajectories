import pandas as pd
import numpy as np
import yaml
from acc_system import AdaptiveCruiseControl

def run_simulation(params_path, tuning_path, sensor_data_path):
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        with open(tuning_path, 'r') as f:
            tuning = yaml.safe_load(f)
            if tuning:
                config['pid_speed'].update(tuning.get('pid_speed', {}))
                config['pid_distance'].update(tuning.get('pid_distance', {}))
    except FileNotFoundError:
        pass

    df_sensor = pd.read_csv(sensor_data_path)
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    ego_speed = 0.0 # Initial speed ~0
    ego_pos = 0.0
    
    lead_pos = None
    results = []
    
    for i, row in df_sensor.iterrows():
        t = row['time']
        lead_speed = row['lead_speed']
        dist_csv = row['distance']
        
        sim_dist = None
        if not np.isnan(lead_speed) and not np.isnan(dist_csv):
            if lead_pos is None:
                # First detection: set lead position relative to current sim ego
                lead_pos = ego_pos + dist_csv
            else:
                # Subsequent detections: update lead position using its speed
                lead_pos += lead_speed * dt
            sim_dist = lead_pos - ego_pos
        else:
            lead_pos = None # Reset if lead disappears
        
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, sim_dist, dt)
        
        # Calculate TTC for output
        ttc = float('nan')
        if sim_dist is not None and lead_speed is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = sim_dist / rel_speed

        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': sim_dist,
            'ttc': ttc
        })
        
        # Update ego vehicle state
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed) # Speed cannot be negative
        ego_pos += ego_speed * dt
        
    return pd.DataFrame(results)

if __name__ == "__main__":
    results_df = run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv')
    results_df.to_csv('simulation_results.csv', index=False)

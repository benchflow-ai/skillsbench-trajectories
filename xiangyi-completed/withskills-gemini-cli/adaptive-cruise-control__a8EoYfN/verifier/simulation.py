import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation(params_path, tuning_path, sensor_path, output_path):
    # Load parameters
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuning results
    try:
        with open(tuning_path, 'r') as f:
            tuning = yaml.safe_load(f)
        if tuning:
            config['pid_speed'].update(tuning['pid_speed'])
            config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass

    # Load sensor data
    sensor_df = pd.read_csv(sensor_path)
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    
    results = []
    
    for i, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        distance_recorded = row['distance']
        
        current_distance = np.nan
        if not np.isnan(distance_recorded) and not np.isnan(lead_speed):
            if lead_pos is None:
                lead_pos = ego_pos + distance_recorded
            else:
                lead_pos += lead_speed * dt
            current_distance = lead_pos - ego_pos
        else:
            lead_pos = None
        
        # Compute ACC command
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, current_distance, dt)
        
        # TTC
        ttc = None
        if not np.isnan(lead_speed) and not np.isnan(current_distance):
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = current_distance / rel_speed
        
        # Store results BEFORE update to reflect state at start of interval
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': current_distance,
            'ttc': ttc
        })
        
        # Update ego for next step
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_pos += ego_speed * dt
        
    res_df = pd.DataFrame(results)
    # Ensure column order
    cols = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    res_df = res_df[cols]
    res_df.to_csv(output_path, index=False)
    return res_df

if __name__ == "__main__":
    run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv', 'simulation_results.csv')
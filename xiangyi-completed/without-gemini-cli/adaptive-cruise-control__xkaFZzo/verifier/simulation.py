import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl
import os

def run_simulation(params_file, tuning_file, sensor_file):
    # Load parameters
    with open(params_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuning results if available, else use defaults from config
    if os.path.exists(tuning_file):
        with open(tuning_file, 'r') as f:
            tuning = yaml.safe_load(f)
        speed_params = tuning['pid_speed']
        distance_params = tuning['pid_distance']
    else:
        speed_params = config['pid_speed']
        distance_params = config['pid_distance']

    # Load sensor data
    df_sensor = pd.read_csv(sensor_file)
    dt = config['simulation']['dt']
    
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_params(speed_params, distance_params)
    
    ego_speed = 0.0
    ego_pos = 0.0
    
    results = []
    distance_sim = np.nan
    prev_lead_speed = np.nan
    
    for i in range(len(df_sensor)):
        row = df_sensor.iloc[i]
        t = row['time']
        lead_speed_csv = row['lead_speed']
        distance_csv = row['distance']
        
        # Update distance_sim
        if not np.isnan(distance_csv):
            if np.isnan(distance_sim):
                # First time lead vehicle is detected
                distance_sim = distance_csv
            else:
                # Evolve distance based on relative speed from previous step
                # We use the lead_speed from the CSV and our own simulated ego_speed
                if not np.isnan(prev_lead_speed):
                    distance_sim += (prev_lead_speed - ego_speed) * dt
        else:
            distance_sim = np.nan
            
        # ACC compute
        accel_cmd, mode, d_error = acc.compute(ego_speed, lead_speed_csv, distance_sim, dt)
        
        # Calculate TTC for simulation results
        ttc = np.nan
        if not np.isnan(lead_speed_csv) and not np.isnan(distance_sim):
            rel_speed = ego_speed - lead_speed_csv
            if rel_speed > 0:
                ttc = distance_sim / rel_speed
        
        # Record results
        def safe_nan(val):
            if val is None: return None
            if isinstance(val, (float, np.float64)) and np.isnan(val): return None
            return float(val)

        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': safe_nan(d_error),
            'distance': safe_nan(distance_sim),
            'ttc': safe_nan(ttc)
        })
        
        # Update state for next step
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_pos += ego_speed * dt
        prev_lead_speed = lead_speed_csv

    return pd.DataFrame(results)

    return pd.DataFrame(results)

if __name__ == "__main__":
    df_results = run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv')
    
    # Ensure exact column order and format
    output_columns = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    df_results = df_results[output_columns]
    
    # Fill NaN with empty strings or appropriate values if needed, but CSV usually handles NaNs as empty
    df_results.to_csv('simulation_results.csv', index=False)

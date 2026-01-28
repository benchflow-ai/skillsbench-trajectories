import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load Params
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load Tuning Results
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'] = tuning['pid_speed']
            config['pid_distance'] = tuning['pid_distance']
    except FileNotFoundError:
        print("tuning_results.yaml not found. Using default params.")

    # Load Data
    data = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    
    # State
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = 0.0 
    lead_active = False
    
    results = []
    
    for i, row in data.iterrows():
        time = row['time']
        lead_speed_input = row['lead_speed']
        dist_input = row['distance']
        
        # Determine Lead State and Position
        current_lead_speed = None
        current_distance = None
        
        if pd.notna(lead_speed_input) and pd.notna(dist_input):
            if not lead_active:
                lead_pos = ego_pos + dist_input
                lead_active = True
            
            current_lead_speed = lead_speed_input
            current_distance = lead_pos - ego_pos
        else:
            lead_active = False
            current_lead_speed = None
            current_distance = None
            
        # Run ACC
        accel_cmd, mode, dist_err = acc.compute(ego_speed, current_lead_speed, current_distance, dt)
        
        # Calculate TTC for logging
        ttc = None
        if current_distance is not None and current_lead_speed is not None:
            rel_spd = ego_speed - current_lead_speed
            if rel_spd > 0.001:
                ttc = current_distance / rel_spd
        
        # Log result
        results.append({
            'time': time,
            'ego_speed': float(f"{ego_speed:.2f}"),
            'acceleration_cmd': float(f"{accel_cmd:.2f}"),
            'mode': mode,
            'distance_error': float(f"{dist_err:.2f}") if dist_err is not None else '',
            'distance': float(f"{current_distance:.2f}") if current_distance is not None else '',
            'ttc': float(f"{ttc:.2f}") if ttc is not None else ''
        })
        
        # Physics Update
        ego_speed += accel_cmd * dt
        if ego_speed < 0: ego_speed = 0
        ego_pos += ego_speed * dt
        
        if lead_active:
             lead_pos += lead_speed_input * dt
             
    # Save Results
    df_res = pd.DataFrame(results)
    df_res.to_csv('simulation_results.csv', index=False)
    print("Simulation complete. Results saved.")

if __name__ == '__main__':
    run_simulation()

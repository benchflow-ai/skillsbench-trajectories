import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def run():
    # Load config
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)
        
    # Load tuned PID params
    with open('tuning_results.yaml', 'r') as f:
        tuning_results = yaml.safe_load(f)
        
    # Merge PID params into config
    base_config['pid_speed'] = tuning_results['pid_speed']
    base_config['pid_distance'] = tuning_results['pid_distance']
    
    # Load sensor data
    df = pd.read_csv('sensor_data.csv')
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(base_config)
    
    # Simulation State
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    
    dt = base_config['simulation']['dt']
    
    results = []
    
    for i, row in df.iterrows():
        time = row['time']
        rec_lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        rec_dist = row['distance'] if pd.notna(row['distance']) else None
        
        # Lead Position Logic (Same as tune_pid.py)
        if rec_lead_speed is not None and rec_dist is not None:
            if lead_pos is None:
                lead_pos = ego_pos + rec_dist
            else:
                lead_pos += rec_lead_speed * dt
        else:
            lead_pos = None
            
        # Calculate simulation distance
        distance = None
        if lead_pos is not None:
            distance = lead_pos - ego_pos
            
        # ACC Compute
        accel_cmd, mode, distance_error = acc.compute(ego_speed, rec_lead_speed, distance, dt)
        
        # Calculate TTC for logging
        ttc = acc.calculate_ttc(distance, ego_speed, rec_lead_speed)
        
        # Log before update (state at time t)
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })
        
        # Physics update
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_pos += ego_speed * dt
        
    # Save to CSV
    # Columns: time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
    out_df = pd.DataFrame(results)
    out_df.to_csv('simulation_results.csv', index=False)
    print("Simulation complete. Results saved to simulation_results.csv")

if __name__ == '__main__':
    run()

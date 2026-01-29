import pandas as pd
import yaml
import numpy as np
import math
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuned PID gains
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            if tuning:
                if 'pid_speed' in tuning:
                    config['pid_speed'].update(tuning['pid_speed'])
                if 'pid_distance' in tuning:
                    config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    ego_speed = 0.0
    # Start back to avoid overtaking
    ego_pos = -150.0
    
    pos_ego_rec = 0.0
    v_ego_rec_prev = 0.0
    
    results = []
    
    for i, row in sensor_data.iterrows():
        t = row['time']
        v_ego_rec = row['ego_speed']
        
        # Reconstruct lead vehicle absolute position if detected
        dist_rec = row['distance']
        if not pd.isna(dist_rec):
            pos_lead = pos_ego_rec + dist_rec
            lead_speed = row['lead_speed']
            my_dist = pos_lead - ego_pos
            
            if my_dist > 0:
                ttc = my_dist / (ego_speed - lead_speed) if ego_speed > lead_speed else float('inf')
            else:
                ttc = 0.0
        else:
            my_dist = None
            lead_speed = None
            ttc = None
            
        # Compute ACC command
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, my_dist, dt)
        
        results.append({
            'time': t,
            'ego_speed': round(ego_speed, 6),
            'acceleration_cmd': round(accel_cmd, 6),
            'mode': mode,
            'distance_error': round(dist_err, 6) if dist_err is not None else None,
            'distance': round(my_dist, 6) if my_dist is not None else None,
            'ttc': round(ttc, 6) if ttc is not None else None
        })
        
        # Update ego state
        drag_force = config['vehicle']['drag_coefficient'] * (ego_speed**2)
        drag_accel = drag_force / config['vehicle']['mass']
        actual_accel = accel_cmd - drag_accel
        
        ego_speed += actual_accel * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt
        
        # Update recorded ego position
        pos_ego_rec += v_ego_rec_prev * dt
        v_ego_rec_prev = v_ego_rec

    # Save results
    df_results = pd.DataFrame(results)
    df_results = df_results[['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']]
    df_results.to_csv('simulation_results.csv', index=False)
    return df_results

if __name__ == "__main__":
    run_simulation()
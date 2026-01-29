import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'].update(tuning['pid_speed'])
            config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass

    sensor_df = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)
    
    ego_speed = 0.0
    results = []
    
    for i, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        my_distance = row['distance']
        
        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, my_distance, dt)
        
        ttc = None
        if my_distance is not None and not pd.isna(my_distance):
            if lead_speed is not None and not pd.isna(lead_speed):
                rel_speed = ego_speed - lead_speed
                if rel_speed > 0:
                    ttc = my_distance / rel_speed
        
        # Store results
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 3),
            'acceleration_cmd': round(accel_cmd, 3),
            'mode': mode,
            'distance_error': round(distance_error, 3) if distance_error is not None else None,
            'distance': round(my_distance, 3) if my_distance is not None else None,
            'ttc': round(ttc, 3) if ttc is not None else None
        })
        
        # Update states
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False)
    return results_df

if __name__ == "__main__":
    run_simulation()

import pandas as pd
import yaml
import os
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuning results if available, otherwise use defaults from config
    if os.path.exists('tuning_results.yaml'):
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            if 'pid_speed' in tuning:
                config['pid_speed'].update(tuning['pid_speed'])
            if 'pid_distance' in tuning:
                config['pid_distance'].update(tuning['pid_distance'])

    # Load sensor data
    sensor_df = pd.read_csv('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    
    results = []
    ego_speed = sensor_df.iloc[0]['ego_speed']
    ego_pos = 0.0
    recorded_ego_pos = 0.0
    dt = config['simulation']['dt']
    
    for i, row in sensor_df.iterrows():
        t = row['time']
        lead_speed = row['lead_speed']
        rec_distance = row['distance']
        rec_ego_speed = row['ego_speed']
        
        # Handle lead vehicle presence
        sim_distance = None
        ttc = None
        if not pd.isna(rec_distance):
            # Lead position relative to start
            lead_pos = recorded_ego_pos + rec_distance
            sim_distance = lead_pos - ego_pos
            
            if lead_speed is not None and not pd.isna(lead_speed):
                relative_speed = ego_speed - lead_speed
                if relative_speed > 0:
                    ttc = sim_distance / relative_speed
        
        # Convert NaN to None for ACC compute
        ls_input = lead_speed if not pd.isna(lead_speed) else None
        dist_input = sim_distance if sim_distance is not None else None
        
        # Compute ACC command
        accel_cmd, mode, dist_err = acc.compute(ego_speed, ls_input, dist_input, dt)
        
        # Store results
        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_err, 2) if dist_err is not None else None,
            'distance': round(sim_distance, 2) if sim_distance is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        })
        
        # Update simulation state
        ego_pos += ego_speed * dt
        recorded_ego_pos += rec_ego_speed * dt
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

    # Save results
    result_df = pd.DataFrame(results)
    result_df.to_csv('simulation_results.csv', index=False)
    return result_df

if __name__ == "__main__":
    run_simulation()

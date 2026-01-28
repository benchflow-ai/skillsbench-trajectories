import pandas as pd
import yaml
import os
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load vehicle params
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    # Load tuning results
    if os.path.exists('tuning_results.yaml'):
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            if 'pid_speed' in tuning:
                config['pid_speed'].update(tuning['pid_speed'])
            if 'pid_distance' in tuning:
                config['pid_distance'].update(tuning['pid_distance'])
            
    # Load sensor data
    df = pd.read_csv('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    ego_speed = df.iloc[0]['ego_speed']
    ego_pos = 0.0
    lead_pos = None
    results = []
    
    for i, row in df.iterrows():
        lead_speed_csv = row['lead_speed']
        orig_dist_csv = row['distance']
        
        lead_present = not pd.isna(lead_speed_csv) and not pd.isna(orig_dist_csv)
        
        current_distance = None
        ttc = None
        lead_speed_val = None
        
        if lead_present:
            if lead_pos is None:
                # First detection: place lead vehicle relative to current ego_pos
                lead_pos = ego_pos + orig_dist_csv
            else:
                # Update lead position based on its speed
                lead_pos += lead_speed_csv * dt
                
            current_distance = lead_pos - ego_pos
            lead_speed_val = lead_speed_csv
            rel_speed = ego_speed - lead_speed_val
            if rel_speed > 0:
                ttc = current_distance / rel_speed
        else:
            # If lead vehicle disappears, reset lead_pos
            lead_pos = None
        
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed_val, current_distance, dt)
        
        res_row = {
            'time': round(row['time'], 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_err, 2) if dist_err is not None else None,
            'distance': round(current_distance, 2) if current_distance is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        }
        results.append(res_row)
        
        # Update simulated state
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_pos += ego_speed * dt
        
    # Save results
    res_df = pd.DataFrame(results)
    res_df = res_df[['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']]
    res_df.to_csv('simulation_results.csv', index=False)
    return results

if __name__ == "__main__":
    run_simulation()
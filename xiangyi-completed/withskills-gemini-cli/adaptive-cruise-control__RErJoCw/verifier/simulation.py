import pandas as pd
import yaml
import os
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    if os.path.exists('tuning_results.yaml'):
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            if tuning:
                if 'pid_speed' in tuning:
                    config['pid_speed'].update(tuning['pid_speed'])
                if 'pid_distance' in tuning:
                    config['pid_distance'].update(tuning['pid_distance'])
    return config

def run_simulation():
    config = load_config()
    df_sensor = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    
    acc = AdaptiveCruiseControl(config)
    
    ego_speed = 0.0
    current_distance = None
    prev_lead_speed = None
    
    results = []
    
    for i, row in df_sensor.iterrows():
        t = row['time']
        lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        # Handle lead vehicle appearance/dynamics
        if not pd.isna(lead_speed):
            if current_distance is None:
                # Lead vehicle just appeared
                current_distance = csv_distance
            else:
                # Update distance based on relative speed from PREVIOUS step
                # d(t) = d(t-dt) + (v_lead(t-dt) - v_ego(t-dt)) * dt
                # However, for the very first step of lead detection, we use the CSV distance.
                # In subsequent steps, we integrate.
                current_distance += (prev_lead_speed - ego_speed) * dt
            
            # TTC calculation for logging
            relative_speed = ego_speed - lead_speed
            ttc = current_distance / relative_speed if relative_speed > 0 else None
        else:
            current_distance = None
            ttc = None
            
        # Compute ACC command
        # Note: acc.compute handles None for lead_speed/distance
        accel_cmd, mode, dist_error = acc.compute(
            ego_speed, 
            None if pd.isna(lead_speed) else lead_speed,
            current_distance,
            dt
        )
        
        # Record state at time t
        results.append({
            'time': t,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else None,
            'distance': round(current_distance, 2) if current_distance is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        })
        
        # Update ego speed for NEXT step
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        prev_lead_speed = lead_speed
        
    df_results = pd.DataFrame(results)
    df_results.to_csv('simulation_results.csv', index=False)
    return df_results

if __name__ == "__main__":
    run_simulation()

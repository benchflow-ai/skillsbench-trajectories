import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Load data
    df = pd.read_csv('sensor_data.csv')
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    acc.update_gains(tuning['pid_speed'], tuning['pid_distance'])
    
    dt = config['simulation']['dt']
    
    # Simulation State
    my_ego_speed = 0.0
    my_ego_pos = 0.0
    lead_pos = None
    
    results = []
    
    for i, row in df.iterrows():
        time = row['time']
        
        # Read sensor data
        csv_lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        csv_distance = row['distance'] if pd.notna(row['distance']) else None
        
        # Update Lead Position
        if csv_lead_speed is not None and csv_distance is not None:
            if lead_pos is None:
                # Lead vehicle just appeared (or re-appeared)
                # Initialize its position relative to ME based on the sensor measurement
                lead_pos = my_ego_pos + csv_distance
            else:
                # Propagate lead position using its speed
                lead_pos += csv_lead_speed * dt
        else:
            # Lost track of lead vehicle
            lead_pos = None
        
        # Calculate current distance based on MY position
        current_distance = None
        if lead_pos is not None:
            current_distance = lead_pos - my_ego_pos
        
        # Run ACC
        accel_cmd, mode, dist_error = acc.compute(my_ego_speed, csv_lead_speed, current_distance, dt)
        
        # Calculate TTC for logging
        ttc = None
        if mode != 'cruise' and current_distance is not None and csv_lead_speed is not None:
            rel_speed = my_ego_speed - csv_lead_speed
            if rel_speed > 0:
                ttc = current_distance / rel_speed
        
        # Log result
        results.append({
            'time': time,
            'ego_speed': my_ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': current_distance,
            'ttc': ttc
        })
        
        # Physics Update (Ego)
        my_ego_speed += accel_cmd * dt
        if my_ego_speed < 0: my_ego_speed = 0.0
        
        my_ego_pos += my_ego_speed * dt

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False, float_format='%.2f')

if __name__ == '__main__':
    run_simulation()
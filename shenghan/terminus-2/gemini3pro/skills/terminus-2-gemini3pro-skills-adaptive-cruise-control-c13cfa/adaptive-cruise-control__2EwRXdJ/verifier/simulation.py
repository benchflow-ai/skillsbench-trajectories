import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl

def run_simulation():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'] = tuning['pid_speed']
            config['pid_distance'] = tuning['pid_distance']
    except FileNotFoundError:
        print('Warning: tuning_results.yaml not found, using defaults')

    data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    results = []
    
    ego_speed = 0.0
    sim_distance = None
    
    for i, row in data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if not pd.isna(row['lead_speed']) else None
        csv_distance = row['distance'] if not pd.isna(row['distance']) else None
        
        # Update sim_distance logic
        if lead_speed is not None:
            if sim_distance is None:
                # Car appeared, reset to scenario distance
                sim_distance = csv_distance
            else:
                # Update based on relative speed
                # sim_distance changes by (lead_speed - ego_speed) * dt
                # But we update it AFTER computing control for the NEXT step
                # For the current step, we use the current sim_distance
                pass
        else:
            sim_distance = None
            
        # Compute control
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, sim_distance, dt)
        
        # Calculate TTC for reporting
        ttc = None
        if lead_speed is not None and sim_distance is not None:
             rel_speed = ego_speed - lead_speed
             if rel_speed > 0:
                 ttc = sim_distance / rel_speed
        
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': sim_distance,
            'ttc': ttc
        })
        
        # Update Physics
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
        if sim_distance is not None and lead_speed is not None:
            sim_distance += (lead_speed - ego_speed) * dt
            
    df = pd.DataFrame(results)
    df.to_csv('simulation_results.csv', index=False, float_format='%.2f')

if __name__ == '__main__':
    run_simulation()

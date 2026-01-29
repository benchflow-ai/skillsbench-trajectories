import pandas as pd
import yaml
import math
from acc_system import AdaptiveCruiseControl

def run_final_simulation():
    # Load parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuned gains
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    
    config['pid_speed'].update(tuning['pid_speed'])
    config['pid_distance'].update(tuning['pid_distance'])
    
    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    ego_speed = 0.0
    sim_distance = None
    
    results = []
    
    for i, row in sensor_data.iterrows():
        t = row['time']
        lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        # Initialize or update simulated distance
        if not pd.isna(csv_distance):
            if sim_distance is None:
                sim_distance = csv_distance
            else:
                if i > 0:
                    prev_ego_speed = results[-1]['ego_speed']
                    prev_lead_speed = sensor_data.iloc[i-1]['lead_speed']
                    if not pd.isna(prev_lead_speed):
                        sim_distance += (prev_lead_speed - prev_ego_speed) * dt
        else:
            sim_distance = None

        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, sim_distance, dt)
        
        # Calculate TTC for output
        ttc = None
        if mode != 'cruise' and not pd.isna(lead_speed) and sim_distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = sim_distance / rel_speed

        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 3),
            'acceleration_cmd': round(accel_cmd, 3),
            'mode': mode,
            'distance_error': round(dist_err, 3) if dist_err is not None else None,
            'distance': round(sim_distance, 3) if sim_distance is not None else None,
            'ttc': round(ttc, 3) if ttc is not None else None
        })
        
        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)
        
    df_results = pd.DataFrame(results)
    # Ensure exact column order: time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
    df_results = df_results[['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']]
    df_results.to_csv('simulation_results.csv', index=False)
    print(f"Simulation complete. Results saved to simulation_results.csv. Total rows: {len(df_results)}")

if __name__ == "__main__":
    run_final_simulation()

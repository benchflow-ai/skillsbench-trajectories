
import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load config
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuning results
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
        # Update config with tuned gains
        if 'pid_speed' in tuning:
            config['pid_speed'].update(tuning['pid_speed'])
        if 'pid_distance' in tuning:
            config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        print("tuning_results.yaml not found, using default gains from vehicle_params.yaml")
    
    # Load sensor data
    df_sensor = pd.read_csv('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    ego_speed = df_sensor['ego_speed'].iloc[0]
    ego_pos_csv = 0.0
    ego_pos_sim = 0.0
    
    results = []
    
    for i in range(len(df_sensor)):
        row = df_sensor.iloc[i]
        t = row['time']
        lead_speed_csv = row['lead_speed']
        distance_csv = row['distance']
        ego_speed_csv = row['ego_speed']
        
        # Handle NaN
        if pd.isna(lead_speed_csv):
            lead_speed = None
        else:
            lead_speed = float(lead_speed_csv)
            
        if pd.isna(distance_csv):
            distance = None
        else:
            # Adjust distance based on our simulated ego speed vs csv ego speed
            distance = float(distance_csv) + (ego_pos_csv - ego_pos_sim)

        # Compute ACC command
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        # TTC calculation for results
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = float(distance / rel_speed)
            else:
                ttc = float('inf')

        # Store results
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': distance,
            'ttc': ttc
        })
        
        # Update state for next step
        ego_pos_csv += ego_speed_csv * dt
        ego_pos_sim += ego_speed * dt
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed) # Speed cannot be negative
        
    # Save results
    res_df = pd.DataFrame(results)
    # Ensure exact column order: time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
    res_df = res_df[['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']]
    res_df.to_csv('simulation_results.csv', index=False)
    return res_df

if __name__ == "__main__":
    run_simulation()

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
        
    # Update config with tuned gains
    if 'pid_speed' in tuning:
        config['pid_speed'] = tuning['pid_speed']
    if 'pid_distance' in tuning:
        config['pid_distance'] = tuning['pid_distance']
        
    return config

def run_simulation():
    config = load_config()
    acc = AdaptiveCruiseControl(config)
    
    # Load Sensor Data
    df = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    
    # Simulation State
    sim_ego_speed = 0.0
    sim_ego_pos = 0.0
    
    # Lead Vehicle State
    lead_active = False
    lead_pos = 0.0
    
    results = []
    
    # Pre-load columns for speed
    lead_speeds = df['lead_speed'].values
    distances = df['distance'].values
    
    for i in range(len(df)):
        t = df.loc[i, 'time']
        
        # Get Input Data
        csv_lead_speed = lead_speeds[i]
        csv_distance = distances[i]
        
        # Handle Lead Vehicle Spawning and Update
        current_lead_speed = None
        sim_distance = None
        
        if not np.isnan(csv_lead_speed):
            # Lead vehicle exists in data
            if not lead_active:
                # First appearance: Spawn relative to current simulated ego position
                # ensuring the initial relative distance matches the scenario
                lead_active = True
                lead_pos = sim_ego_pos + csv_distance
            else:
                # Update lead position based on its speed
                # Simple Euler: pos += speed * dt
                # Use previous step's speed if available, or current. 
                # Since we iterate, we can just use current speed for forward update 
                # or better, use the speed from the data which represents speed at this time.
                pass
            
            current_lead_speed = csv_lead_speed
            sim_distance = lead_pos - sim_ego_pos
            
        else:
            lead_active = False
            sim_distance = None
            
        # ACC Compute
        accel_cmd, mode, dist_error, ttc = acc.compute(sim_ego_speed, current_lead_speed, sim_distance, dt)
        
        # Store Results
        row = {
            'time': t,
            'ego_speed': sim_ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error if dist_error is not None else '',
            'distance': sim_distance if sim_distance is not None else '',
            'ttc': ttc if ttc is not None and ttc != float('inf') else ''
        }
        results.append(row)
        
        # Update Physics for Next Step
        sim_ego_speed += accel_cmd * dt
        sim_ego_speed = max(0.0, sim_ego_speed)
        sim_ego_pos += sim_ego_speed * dt
        
        # Update Lead Position for Next Step
        if lead_active:
            lead_pos += current_lead_speed * dt
        
    # Save Results
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False)
    print("Simulation complete. Results saved to simulation_results.csv")

if __name__ == "__main__":
    run_simulation()
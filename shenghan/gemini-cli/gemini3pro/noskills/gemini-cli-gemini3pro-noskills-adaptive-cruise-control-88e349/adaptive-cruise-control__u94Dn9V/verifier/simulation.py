import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
        config['pid_speed'] = tuning['pid_speed']
        config['pid_distance'] = tuning['pid_distance']
    return config

def main():
    config = load_config()
    df = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    mass = config['vehicle']['mass']
    drag_coeff = config['vehicle']['drag_coefficient']
    
    # Simulation
    acc = AdaptiveCruiseControl(config)
    
    sim_ego_speed = 0.0
    sim_ego_pos = 0.0
    
    # Lead State
    lead_pos = None
    prev_lead_valid = False
    
    results = []
    
    # Data columns
    lead_speeds = df['lead_speed'].values
    distances = df['distance'].values
    times = df['time'].values
    
    for i in range(len(df)):
        t = times[i]
        l_speed_rec = lead_speeds[i]
        dist_rec = distances[i]
        
        is_lead_valid = not pd.isna(l_speed_rec)
        
        # Update Lead Position
        if is_lead_valid:
            if not prev_lead_valid:
                # Just appeared. Spawn relative to current Ego Pos.
                # Use the recorded distance to spawn it.
                if pd.isna(dist_rec):
                    # Should not happen based on CSV structure, but safety
                    lead_pos = sim_ego_pos + 100.0 
                else:
                    lead_pos = sim_ego_pos + dist_rec
            else:
                # Continue integrating
                # Use previous speed? Or current? Euler forward: pos += vel * dt.
                # using current step velocity for simplicity
                lead_pos += l_speed_rec * dt
        else:
            lead_pos = None
            
        prev_lead_valid = is_lead_valid
        
        # Calculate current distance
        current_distance = None
        if lead_pos is not None:
            current_distance = lead_pos - sim_ego_pos
            
        # Compute Control
        acc_cmd, mode, dist_err = acc.compute(sim_ego_speed, l_speed_rec if is_lead_valid else None, current_distance, dt)
        
        # TTC Calculation for logging
        ttc = None
        if is_lead_valid and current_distance is not None:
            rel_speed = sim_ego_speed - l_speed_rec
            if rel_speed > 0:
                ttc = current_distance / rel_speed
        
        # Log
        results.append({
            'time': t,
            'ego_speed': sim_ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': dist_err if dist_err is not None else '',
            'distance': current_distance if current_distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })
        
        # Physics Update
        a_drag = (drag_coeff * sim_ego_speed**2 * np.sign(sim_ego_speed)) / mass
        
        sim_ego_speed += (acc_cmd - a_drag) * dt
        if sim_ego_speed < 0: sim_ego_speed = 0
        
        sim_ego_pos += sim_ego_speed * dt

    # Save to CSV
    res_df = pd.DataFrame(results)
    cols = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    res_df = res_df[cols]
    res_df.to_csv('simulation_results.csv', index=False, float_format='%.2f')

if __name__ == "__main__":
    main()
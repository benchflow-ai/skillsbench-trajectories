import pandas as pd
import numpy as np
import yaml
from acc_system import AdaptiveCruiseControl

def run_simulation(config, df, duration=150.0):
    acc = AdaptiveCruiseControl(config)
    
    dt = 0.1
    steps = int(duration / dt)
    
    # Ego state
    ego_speed = 0.0
    ego_pos = 0.0
    
    # Lead state
    sim_lead_pos = None
    lead_active = False
    
    # History
    history = {
        'time': [],
        'ego_speed': [],
        'distance': [],
        'distance_error': [],
        'acceleration_cmd': [],
        'mode': [],
        'ttc': []
    }
    
    for i in range(steps + 1):
        t = i * dt
        if i >= len(df):
            break
            
        row = df.iloc[i]
        
        # Read inputs from CSV
        csv_lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        # Determine lead vehicle state in simulation
        current_dist = None
        current_lead_speed = None
        
        if not pd.isna(csv_distance) and not pd.isna(csv_lead_speed):
            # Lead vehicle exists in data
            if not lead_active:
                # First detection! Spawn lead vehicle relative to current ego pos
                lead_active = True
                sim_lead_pos = ego_pos + csv_distance
            else:
                # Update lead position based on its speed
                # (We use the previous step's lead speed to update pos? 
                # Or current? Euler: pos += v * dt)
                # Let's use current row lead_speed for next step or this step?
                # Simple Euler: pos_new = pos_old + v * dt.
                # But here we are iterating.
                # We need to update sim_lead_pos from previous step.
                # But we don't have "previous" row easily accessible unless we track it.
                # Actually, we can update sim_lead_pos at the END of the loop for the next step.
                pass
            
            current_lead_speed = csv_lead_speed
            current_dist = sim_lead_pos - ego_pos
        else:
            lead_active = False
            sim_lead_pos = None
            
        # ACC Compute
        accel_cmd, mode, dist_err = acc.compute(ego_speed, current_lead_speed, current_dist, dt)
        
        # Record stats
        ttc = None
        if current_dist is not None and current_lead_speed is not None:
             rel_v = ego_speed - current_lead_speed
             if rel_v > 0:
                 ttc = current_dist / rel_v
        
        history['time'].append(t)
        history['ego_speed'].append(ego_speed)
        history['acceleration_cmd'].append(accel_cmd)
        history['mode'].append(mode)
        history['distance_error'].append(dist_err)
        history['distance'].append(current_dist)
        history['ttc'].append(ttc)
        
        # Physics update for NEXT step
        # Ego
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt
        
        # Lead
        if lead_active:
            # Update lead position for next step using CURRENT lead speed
            sim_lead_pos += current_lead_speed * dt
            
    return history

def tune():
    # Load base config
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)
    
    df = pd.read_csv('sensor_data.csv')
    
    # 1. Tune Speed PID (Cruise Phase: t=0 to 30)
    print("Tuning Speed PID...")
    best_speed_score = float('inf')
    best_speed_gains = (0,0,0)
    
    # Grid search ranges
    # Increased Kd range as oscillation might be an issue
    kps = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
    kis = [0.0, 0.01, 0.05, 0.1, 0.5]
    kds = [0.0, 0.1, 0.5, 1.0, 2.0, 4.0]
    
    for kp in kps:
        for ki in kis:
            for kd in kds:
                config = base_config.copy()
                config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
                config['pid_distance'] = {'kp': 1.0, 'ki': 0.0, 'kd': 0.0}
                
                res = run_simulation(config, df, duration=30.0)
                
                speeds = np.array(res['ego_speed'])
                times = np.array(res['time'])
                
                # Rise time
                reached_90 = np.where(speeds >= 27.0)[0]
                if len(reached_90) > 0:
                    rise_time = times[reached_90[0]]
                else:
                    rise_time = 30.0 
                    
                # Overshoot
                max_speed = np.max(speeds)
                overshoot_pct = (max_speed - 30.0) / 30.0 * 100
                
                # SS Error (at 30s)
                ss_error = abs(speeds[-1] - 30.0)
                
                valid = True
                if rise_time > 10.0: valid = False
                if overshoot_pct > 5.0: valid = False
                if ss_error > 0.5: valid = False 
                
                score = (rise_time * 1.0) + (max(0, overshoot_pct) * 5.0) + (ss_error * 10.0)
                
                if not valid:
                    score += 1000.0
                    
                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_gains = (kp, ki, kd)

    print(f"Best Speed Gains: {best_speed_gains} Score: {best_speed_score}")
    
    # 2. Tune Distance PID (Follow Phase)
    print("Tuning Distance PID...")
    best_dist_score = float('inf')
    best_dist_gains = (0,0,0)
    
    base_config['pid_speed'] = {'kp': best_speed_gains[0], 'ki': best_speed_gains[1], 'kd': best_speed_gains[2]}
    
    # Expanded ranges
    kps_d = [2.0, 4.0, 6.0, 8.0, 10.0]
    kis_d = [0.1, 0.3, 0.5, 0.8, 1.0, 2.0]
    kds_d = [0.0, 0.5, 1.0, 2.0, 4.0]
    
    for kp in kps_d:
        for ki in kis_d:
            for kd in kds_d:
                config = base_config.copy()
                config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}
                
                res = run_simulation(config, df, duration=150.0)
                
                # Analysis t=30 to 150
                # Filter valid data
                dist_errors = []
                distances = []
                for d, e in zip(res['distance'], res['distance_error']):
                    if d is not None and e is not None:
                        distances.append(d)
                        dist_errors.append(e)
                
                dist_errors = np.array(dist_errors)
                distances = np.array(distances)
                
                if len(distances) == 0:
                    continue

                # SS Error (last 30s)
                # Assuming steady state is reached
                if len(dist_errors) > 300:
                    ss_dist_error = np.mean(np.abs(dist_errors[-300:]))
                else:
                    ss_dist_error = np.mean(np.abs(dist_errors))

                min_dist = np.min(distances)
                
                valid = True
                if ss_dist_error > 2.0: valid = False
                if min_dist < 5.0: valid = False
                
                score = (ss_dist_error * 10.0) + (max(0, 10.0 - min_dist) * 20.0)
                
                if not valid:
                    score += 2000.0
                
                if score < best_dist_score:
                    best_dist_score = score
                    best_dist_gains = (kp, ki, kd)
                    
    print(f"Best Distance Gains: {best_dist_gains} Score: {best_dist_score}")
    
    # Save results
    results = {
        'pid_speed': {
            'kp': float(best_speed_gains[0]),
            'ki': float(best_speed_gains[1]),
            'kd': float(best_speed_gains[2])
        },
        'pid_distance': {
            'kp': float(best_dist_gains[0]),
            'ki': float(best_dist_gains[1]),
            'kd': float(best_dist_gains[2])
        }
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

if __name__ == '__main__':
    tune()
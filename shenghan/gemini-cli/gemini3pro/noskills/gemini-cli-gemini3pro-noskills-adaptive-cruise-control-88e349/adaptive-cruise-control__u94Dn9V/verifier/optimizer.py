import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)

def load_data():
    return pd.read_csv('sensor_data.csv')

def simulate(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d, config, df):
    # Update config with gains
    config['pid_speed']['kp'] = float(kp_s)
    config['pid_speed']['ki'] = float(ki_s)
    config['pid_speed']['kd'] = float(kd_s)
    config['pid_distance']['kp'] = float(kp_d)
    config['pid_distance']['ki'] = float(ki_d)
    config['pid_distance']['kd'] = float(kd_d)
    
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    mass = config['vehicle']['mass']
    drag_coeff = config['vehicle']['drag_coefficient']
    
    sim_ego_speed = 0.0
    sim_ego_pos = 0.0
    
    lead_pos = None
    prev_lead_valid = False
    
    lead_speeds = df['lead_speed'].values
    distances = df['distance'].values
    times = df['time'].values
    
    sim_data = []
    
    for i, t in enumerate(times):
        l_speed_rec = lead_speeds[i]
        dist_rec = distances[i]
        
        is_lead_valid = not pd.isna(l_speed_rec)
        
        # Update Lead Position
        if is_lead_valid:
            if not prev_lead_valid:
                if pd.isna(dist_rec):
                    lead_pos = sim_ego_pos + 100.0 
                else:
                    lead_pos = sim_ego_pos + dist_rec
            else:
                lead_pos += l_speed_rec * dt
        else:
            lead_pos = None
            
        prev_lead_valid = is_lead_valid
        
        # Calculate current distance
        current_distance = None
        if lead_pos is not None:
            current_distance = lead_pos - sim_ego_pos
        
        # ACC Compute
        acc_cmd, mode, dist_err = acc.compute(sim_ego_speed, l_speed_rec if is_lead_valid else None, current_distance, dt)
        
        # Physics Update
        a_drag = (drag_coeff * sim_ego_speed**2 * np.sign(sim_ego_speed)) / mass
        
        sim_ego_speed += (acc_cmd - a_drag) * dt
        if sim_ego_speed < 0: sim_ego_speed = 0
        
        sim_ego_pos += sim_ego_speed * dt
        
        sim_data.append({
            'time': t,
            'speed': sim_ego_speed,
            'mode': mode,
            'dist_err': dist_err,
            'distance': current_distance
        })
        
    return sim_data

def evaluate_speed_control(sim_data, target_speed=30.0):
    # Evaluate 0 to 25s (Cruise) - Lead appears at 30s
    speeds = [d['speed'] for d in sim_data if d['time'] < 25]
    times = [d['time'] for d in sim_data if d['time'] < 25]
    
    if not speeds: return 999, 999, 999
    
    max_s = max(speeds)
    final_s = speeds[-1]
    
    # Rise Time
    t_10 = next((t for t, s in zip(times, speeds) if s >= 0.1 * target_speed), None)
    t_90 = next((t for t, s in zip(times, speeds) if s >= 0.9 * target_speed), None)
    
    rise_time = 999
    if t_10 and t_90:
        rise_time = t_90 - t_10
        
    overshoot = (max_s - target_speed) / target_speed if max_s > target_speed else 0
    ss_error = abs(target_speed - final_s)
    
    return rise_time, overshoot, ss_error

def evaluate_dist_control(sim_data):
    # Evaluate when mode is 'follow'
    segment = [d for d in sim_data if d['mode'] == 'follow']
    
    if not segment: return 999
    
    dist_errors = [abs(d['dist_err']) for d in segment if d['dist_err'] is not None]
    
    if not dist_errors: return 999
    
    mean_err = np.mean(dist_errors)
    max_err = np.max(dist_errors)
    
    min_dist = min([d['distance'] for d in segment if d['distance'] is not None])
    
    penalty = 0
    if min_dist < 5.0:
        penalty += 1000
    if min_dist < 10.0: # Soft penalty for being close
         penalty += 100
        
    return mean_err + penalty

def tune():
    config = load_config()
    df = load_data()
    
    best_speed_score = float('inf')
    best_speed_params = (0.5, 0.05, 0.5) # Default start
    
    print("Tuning Speed PID...")
    # Using the manual refined range
    for kp in [0.2, 0.5, 0.8, 1.0]:
        for ki in [0.005, 0.01, 0.05, 0.1]:
            for kd in [0.0, 0.5, 1.0, 1.5]:
                data = simulate(kp, ki, kd, 0.1, 0.0, 0.0, config, df)
                rt, os, ss = evaluate_speed_control(data)
                
                valid = rt < 10 and os < 0.05 and ss < 0.5
                score = (rt/10.0) + (os/0.05) + (ss/0.5)
                
                if not valid: score += 100
                
                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_params = (kp, ki, kd)

    print(f"Selected Speed Params: {best_speed_params}")
    
    s_kp, s_ki, s_kd = best_speed_params
    
    best_dist_score = float('inf')
    best_dist_params = (0.5, 0.1, 1.0)
    
    print("Tuning Distance PID...")
    for kp in [0.2, 0.4, 0.6, 0.8, 1.0]:
        for ki in [0.01, 0.05, 0.1, 0.2]:
            for kd in [0.5, 1.0, 1.5, 2.0]:
                data = simulate(s_kp, s_ki, s_kd, kp, ki, kd, config, df)
                score = evaluate_dist_control(data)
                
                if score < best_dist_score:
                    best_dist_score = score
                    best_dist_params = (kp, ki, kd)

    print(f"Selected Dist Params: {best_dist_params}")
    
    results = {
        'pid_speed': {
            'kp': float(best_speed_params[0]),
            'ki': float(best_speed_params[1]),
            'kd': float(best_speed_params[2])
        },
        'pid_distance': {
            'kp': float(best_dist_params[0]),
            'ki': float(best_dist_params[1]),
            'kd': float(best_dist_params[2])
        }
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

if __name__ == "__main__":
    tune()
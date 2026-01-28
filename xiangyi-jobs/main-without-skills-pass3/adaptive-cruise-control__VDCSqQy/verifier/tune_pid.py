import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def evaluate_speed_pid(kp, ki, kd, config):
    config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
    acc = AdaptiveCruiseControl(config)
    
    dt = 0.1
    ego_speed = 0.0
    target_speed = 30.0
    
    times = []
    speeds = []
    
    for t in np.arange(0, 60, dt):
        # Cruise mode (no lead)
        accel, mode, _ = acc.compute(ego_speed, None, None, dt)
        ego_speed += accel * dt
        if ego_speed < 0: ego_speed = 0
        times.append(t)
        speeds.append(ego_speed)
        
    speeds = np.array(speeds)
    
    # Metrics
    # Rise time: time to reach 90% of target? Or 100%? usually 10-90% or 0-100%.
    # Task says "speed rise time < 10s". Let's assume 0 to 98% or similar.
    # Let's say time to reach 30.0 * 0.95 (28.5 m/s)
    reached_idx = np.where(speeds >= target_speed * 0.95)[0]
    rise_time = times[reached_idx[0]] if len(reached_idx) > 0 else 999
    
    overshoot = (np.max(speeds) - target_speed) / target_speed * 100
    final_error = abs(speeds[-1] - target_speed)
    
    score = 0
    if rise_time < 10: score += 100 - rise_time
    else: score -= rise_time * 10
    
    if overshoot < 5: score += 50
    else: score -= overshoot * 10
    
    if final_error < 0.5: score += 50
    else: score -= final_error * 20
    
    return score, rise_time, overshoot, final_error

def evaluate_distance_pid(kp, ki, kd, config):
    config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}
    acc = AdaptiveCruiseControl(config)
    
    dt = 0.1
    ego_speed = 20.0
    ego_pos = 0.0
    lead_speed = 20.0
    lead_pos = 50.0 # Initial gap 50m
    
    # Lead slows down
    
    errors = []
    min_dist = 999
    
    for t in np.arange(0, 60, dt):
        if t > 10:
            lead_speed = 15.0 # Lead slows down
            
        dist = lead_pos - ego_pos
        min_dist = min(min_dist, dist)
        
        accel, mode, dist_err = acc.compute(ego_speed, lead_speed, dist, dt)
        
        ego_speed += accel * dt
        if ego_speed < 0: ego_speed = 0
        ego_pos += ego_speed * dt
        
        lead_pos += lead_speed * dt
        
        if t > 30:
            if dist_err is not None: errors.append(abs(dist_err))
            
    avg_ss_error = np.mean(errors) if errors else 999
    
    score = 0
    if avg_ss_error < 2.0: score += 100 - avg_ss_error
    else: score -= avg_ss_error * 10
    
    if min_dist > 5.0: score += 50
    else: score -= 1000 # Crash or unsafe
    
    return score, avg_ss_error, min_dist

def tune():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    # Tune Speed PID
    best_speed_score = -99999
    best_speed_params = (0.1, 0.01, 0.0)
    
    print("Tuning Speed PID...")
    for kp in [0.2, 0.5, 0.8, 1.0, 1.5]:
        for ki in [0.0, 0.01, 0.05, 0.1]:
            for kd in [0.0, 0.1, 0.5]:
                score, rt, os, fe = evaluate_speed_pid(kp, ki, kd, config.copy())
                if score > best_speed_score:
                    best_speed_score = score
                    best_speed_params = (kp, ki, kd)
                    # print(f"New best speed: {kp, ki, kd} -> RT:{rt:.1f}, OS:{os:.1f}%, Err:{fe:.2f}")

    print(f"Best Speed PID: {best_speed_params}")
    
    # Update config for distance tuning
    config['pid_speed'] = {'kp': best_speed_params[0], 'ki': best_speed_params[1], 'kd': best_speed_params[2]}
    
    # Tune Distance PID
    best_dist_score = -99999
    best_dist_params = (0.1, 0.01, 0.0)
    
    print("Tuning Distance PID...")
    for kp in [0.1, 0.3, 0.5, 0.8]:
        for ki in [0.0, 0.01, 0.05]:
            for kd in [0.0, 0.1, 0.5]:
                score, err, md = evaluate_distance_pid(kp, ki, kd, config.copy())
                if score > best_dist_score:
                    best_dist_score = score
                    best_dist_params = (kp, ki, kd)
                    # print(f"New best dist: {kp, ki, kd} -> Err:{err:.2f}, MinD:{md:.1f}")
                    
    print(f"Best Distance PID: {best_dist_params}")
    
    # Save results
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
    print("Saved tuning_results.yaml")

if __name__ == '__main__':
    tune()

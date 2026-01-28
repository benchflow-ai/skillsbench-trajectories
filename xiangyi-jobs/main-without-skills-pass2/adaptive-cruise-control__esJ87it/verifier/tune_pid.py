import yaml
import math
from acc_system import AdaptiveCruiseControl

def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)

def simulate_step_response(kp, ki, kd, config):
    # Simulate speed control: Target 30m/s from 0
    acc = AdaptiveCruiseControl(config)
    acc.update_gains({'kp': kp, 'ki': ki, 'kd': kd}, {'kp': 0, 'ki': 0, 'kd': 0})
    
    dt = 0.1
    sim_time = 50.0
    steps = int(sim_time / dt)
    ego_speed = 0.0
    
    speeds = []
    times = []
    
    for i in range(steps):
        t = i * dt
        # No lead vehicle -> Cruise mode
        accel, _, _ = acc.compute(ego_speed, None, None, dt)
        ego_speed += accel * dt
        speeds.append(ego_speed)
        times.append(t)
        
    # Metrics
    target = 30.0
    # Rise time: time to go from 10% to 90% of target? Or just time to reach target? 
    # Prompt: speed rise time < 10s. Usually 0-100% or 10-90%.
    # Let's say time to reach 90% of target (27m/s) first time.
    rise_time = None
    for t, v in zip(times, speeds):
        if v >= 0.9 * target:
            rise_time = t
            break
            
    max_speed = max(speeds)
    overshoot = (max_speed - target) / target * 100
    final_speed = speeds[-1]
    steady_state_error = abs(target - final_speed)
    
    valid = True
    if rise_time is None or rise_time > 10.0: valid = False
    if overshoot > 5.0: valid = False
    if steady_state_error > 0.5: valid = False
    
    score = steady_state_error + abs(overshoot) # Minimize this
    return valid, score

def simulate_following(kp, ki, kd, config, speed_gains):
    # Simulate following a car at constant speed or varying
    # Target distance = 10 + 1.5 * ego_speed
    # Let's simulate a lead car moving at 20m/s starting 50m ahead
    acc = AdaptiveCruiseControl(config)
    acc.update_gains(speed_gains, {'kp': kp, 'ki': ki, 'kd': kd})
    
    dt = 0.1
    sim_time = 60.0
    steps = int(sim_time / dt)
    
    ego_speed = 20.0 # Start at same speed
    ego_pos = 0.0
    lead_speed = 20.0
    lead_pos = 50.0 # Initial distance 50m. Desired ~ 10 + 1.5*20 = 40m.
    # Error = 50 - 40 = 10m (Too far)
    
    dist_errors = []
    min_dist = float('inf')
    
    for i in range(steps):
        dist = lead_pos - ego_pos
        min_dist = min(min_dist, dist)
        
        accel, mode, err = acc.compute(ego_speed, lead_speed, dist, dt)
        
        ego_speed += accel * dt
        if ego_speed < 0: ego_speed = 0
        ego_pos += ego_speed * dt
        lead_pos += lead_speed * dt
        
        if err is not None:
            dist_errors.append(abs(err))
            
    final_error = dist_errors[-1]
    
    valid = True
    if final_error > 2.0: valid = False
    if min_dist < 5.0: valid = False
    
    score = final_error
    return valid, score

def tune():
    config = load_config()
    
    # Tune Speed PID
    best_speed_pid = {'kp': 0.5, 'ki': 0.01, 'kd': 0.0}
    best_speed_score = float('inf')
    
    # Coarse grid search for Speed
    # Kp (0,10), Ki [0,5), Kd [0,5)
    # We need rise time < 10s. Higher Kp helps rise time but increases overshoot.
    for kp in [0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]:
        for ki in [0.0, 0.01, 0.05, 0.1, 0.5]:
            for kd in [0.0, 0.1, 0.5, 1.0]:
                valid, score = simulate_step_response(kp, ki, kd, config)
                if valid and score < best_speed_score:
                    best_speed_score = score
                    best_speed_pid = {'kp': kp, 'ki': ki, 'kd': kd}
                    
    print(f"Best Speed PID: {best_speed_pid} Score: {best_speed_score}")
    
    # Tune Distance PID
    best_dist_pid = {'kp': 0.5, 'ki': 0.01, 'kd': 0.0}
    best_dist_score = float('inf')
    
    for kp in [0.1, 0.3, 0.5, 0.8, 1.0, 1.5]:
        for ki in [0.0, 0.01, 0.05, 0.1]:
            for kd in [0.0, 0.1, 0.5]:
                valid, score = simulate_following(kp, ki, kd, config, best_speed_pid)
                if valid and score < best_dist_score:
                    best_dist_score = score
                    best_dist_pid = {'kp': kp, 'ki': ki, 'kd': kd}
                    
    print(f"Best Distance PID: {best_dist_pid} Score: {best_dist_score}")
    
    results = {
        'pid_speed': best_speed_pid,
        'pid_distance': best_dist_pid
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

if __name__ == '__main__':
    tune()

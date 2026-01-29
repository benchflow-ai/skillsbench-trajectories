import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl
from pid_controller import PIDController

def run_speed_simulation(kp, ki, kd, config, duration=60.0, dt=0.1):
    acc = AdaptiveCruiseControl(config)
    acc.update_gains('speed', kp, ki, kd)
    
    ego_speed = 0.0
    times = []
    speeds = []
    
    steps = int(duration / dt)
    for i in range(steps):
        t = i * dt
        # Cruise mode (no lead vehicle)
        accel, _, _, _ = acc.compute(ego_speed, None, None, dt)
        
        # Update physics
        ego_speed += accel * dt
        ego_speed = max(0.0, ego_speed)
        
        times.append(t)
        speeds.append(ego_speed)
        
    return times, speeds

def evaluate_speed(times, speeds, target_speed):
    # Metrics
    # Rise time (10% to 90%)
    t10 = None
    t90 = None
    for t, v in zip(times, speeds):
        if t10 is None and v >= 0.1 * target_speed:
            t10 = t
        if t90 is None and v >= 0.9 * target_speed:
            t90 = t
            break
            
    rise_time = (t90 - t10) if (t10 is not None and t90 is not None) else float('inf')
    
    max_speed = max(speeds)
    overshoot = ((max_speed - target_speed) / target_speed) * 100 if max_speed > target_speed else 0.0
    
    # SS Error (last 5 seconds)
    final_speeds = speeds[-int(5.0/(times[1]-times[0])):]
    ss_error = abs(target_speed - np.mean(final_speeds))
    
    return rise_time, overshoot, ss_error

def run_distance_simulation(kp, ki, kd, config, duration=100.0, dt=0.1):
    acc = AdaptiveCruiseControl(config)
    acc.update_gains('distance', kp, ki, kd)
    # Use already tuned speed gains if needed, but in follow mode speed PID is reset.
    # However, ACC might switch modes. For this test, force follow mode by ensuring lead is close.
    
    ego_speed = 30.0
    lead_speed = 25.0
    distance = 100.0 # Initial distance
    
    # Target distance changes dynamically: time_headway * ego_speed + min_dist
    
    times = []
    distances = []
    errors = []
    min_dists = []
    
    steps = int(duration / dt)
    for i in range(steps):
        t = i * dt
        
        # Physics
        # Update distance
        distance -= (ego_speed - lead_speed) * dt
        
        accel, mode, dist_error, _ = acc.compute(ego_speed, lead_speed, distance, dt)
        
        ego_speed += accel * dt
        ego_speed = max(0.0, ego_speed)
        
        times.append(t)
        distances.append(distance)
        
        # Calculate expected error for metrics
        safe_dist = config['acc_settings']['time_headway'] * ego_speed + config['acc_settings']['min_distance']
        current_error = distance - safe_dist
        errors.append(current_error)
        min_dists.append(distance)
        
    return times, errors, min_dists

def evaluate_distance(times, errors, min_dists):
    # SS Error (last 10 seconds)
    dt = times[1] - times[0]
    final_errors = errors[-int(10.0/dt):]
    ss_error = np.mean(np.abs(final_errors))
    
    min_dist = min(min_dists)
    
    return ss_error, min_dist

def tune():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    # Tune Speed PID
    print("Tuning Speed PID...")
    best_speed_score = float('inf')
    best_speed_params = None
    
    # Coarse grid search based on prompt ranges: kp (0,10), ki [0,5), kd [0,5)
    # To save time, I'll use a sparse grid first or just reasonable engineering guesses.
    # Speed control usually needs Kp, maybe Ki. Kd often 0 for cruise control to avoid jitter.
    
    for kp in [0.1, 0.5, 1.0, 2.0, 5.0]:
        for ki in [0.0, 0.01, 0.05, 0.1, 0.5]:
            for kd in [0.0, 0.1, 0.5, 1.0]:
                times, speeds = run_speed_simulation(kp, ki, kd, config)
                rt, os, ss = evaluate_speed(times, speeds, config['acc_settings']['set_speed'])
                
                # Check constraints
                # rise time < 10s, overshoot < 5%, ss_error < 0.5
                if rt < 10.0 and os < 5.0 and ss < 0.5:
                    score = rt + os + ss * 10 # Weighted score
                    if score < best_speed_score:
                        best_speed_score = score
                        best_speed_params = {'kp': kp, 'ki': ki, 'kd': kd}
                        print(f"New Best Speed: {best_speed_params} (RT={rt:.2f}, OS={os:.2f}, SS={ss:.2f})")
    
    if best_speed_params is None:
        print("Failed to find valid speed params, using fallback")
        best_speed_params = {'kp': 0.5, 'ki': 0.01, 'kd': 0.0}

    # Tune Distance PID
    print("Tuning Distance PID...")
    best_dist_score = float('inf')
    best_dist_params = None
    
    for kp in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 2.0]:
        for ki in [0.0, 0.001, 0.005, 0.01, 0.05]:
            for kd in [0.0, 0.05, 0.1, 0.2, 0.5]:
                times, errors, min_dists = run_distance_simulation(kp, ki, kd, config)
                ss, min_d = evaluate_distance(times, errors, min_dists)
                
                # Constraints: ss_error < 2m, min_dist > 5m
                if ss < 2.0 and min_d > 5.0:
                    score = ss # Minimize steady state error primarily
                    if score < best_dist_score:
                        best_dist_score = score
                        best_dist_params = {'kp': kp, 'ki': ki, 'kd': kd}
                        print(f"New Best Distance: {best_dist_params} (SS={ss:.2f}, MinD={min_d:.2f})")

    if best_dist_params is None:
        print("Failed to find valid distance params, using fallback")
        best_dist_params = {'kp': 0.2, 'ki': 0.01, 'kd': 0.1}
        
    # Save Results
    results = {
        'pid_speed': best_speed_params,
        'pid_distance': best_dist_params
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)
    
    print("Tuning Complete. Results saved to tuning_results.yaml")

if __name__ == "__main__":
    tune()


import yaml
import math
from pid_controller import PIDController

# Simulation constants
DT = 0.1
MAX_ACCEL = 3.0
MAX_DECEL = -8.0
SET_SPEED = 30.0
TIME_HEADWAY = 1.5
MIN_DISTANCE = 10.0

def simulate_speed_step(kp, ki, kd, duration=60.0):
    pid = PIDController(kp, ki, kd)
    ego_speed = 0.0
    times = []
    speeds = []
    
    t = 0.0
    while t < duration:
        error = SET_SPEED - ego_speed
        acc = pid.compute(error, DT)
        acc = max(MAX_DECEL, min(acc, MAX_ACCEL))
        
        ego_speed += acc * DT
        
        times.append(t)
        speeds.append(ego_speed)
        t += DT
        
    return times, speeds

def calculate_speed_metrics(times, speeds):
    # Rise time (10% to 90% of 30.0)
    t10 = None
    t90 = None
    for t, v in zip(times, speeds):
        if t10 is None and v >= 0.1 * SET_SPEED:
            t10 = t
        if t90 is None and v >= 0.9 * SET_SPEED:
            t90 = t
            break
            
    rise_time = (t90 - t10) if (t10 and t90) else float('inf')
    
    # Overshoot
    max_v = max(speeds)
    overshoot = (max_v - SET_SPEED) / SET_SPEED * 100 if max_v > SET_SPEED else 0.0
    
    # SS Error (last 5 seconds)
    final_avg = sum(speeds[-50:]) / 50
    ss_error = abs(SET_SPEED - final_avg)
    
    return rise_time, overshoot, ss_error

def tune_speed_pid():
    best_score = float('inf')
    best_gains = (0.5, 0.0, 0.0) # Default
    
    # Grid search logic
    # Kp: 0.1 to 2.0
    # Ki: 0.0 to 1.0
    # Kd: 0.0 to 1.0
    
    kps = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    kis = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5]
    kds = [0.0, 0.1, 0.5]
    
    for kp in kps:
        for ki in kis:
            for kd in kds:
                times, speeds = simulate_speed_step(kp, ki, kd)
                rt, os, ss = calculate_speed_metrics(times, speeds)
                
                # Check constraints
                # rise time < 10s, overshoot < 5%, ss < 0.5
                if rt < 10.0 and os < 5.0 and ss < 0.5:
                    # Score: Minimize Rise Time + Penalty for Overshoot/SS
                    score = rt + os + ss*10
                    if score < best_score:
                        best_score = score
                        best_gains = (kp, ki, kd)
                        
    return best_gains

def simulate_distance_follow(kp, ki, kd, duration=60.0):
    pid = PIDController(kp, ki, kd)
    ego_speed = 30.0
    lead_speed = 20.0
    distance = 100.0 # Initial large distance
    
    times = []
    dist_errors = []
    
    t = 0.0
    while t < duration:
        # Scenario: Lead car slows down to 20m/s. Ego starts at 30.
        # Desired distance depends on Ego Speed: ego_speed * TH + min_dist
        
        target_dist = ego_speed * TIME_HEADWAY + MIN_DISTANCE
        error = distance - target_dist
        
        # If error is positive (too far), accelerate? 
        # Wait, if distance > target, error > 0. We want to catch up? 
        # Usually ACC tries to maintain gap. 
        # If we are too far, we can accelerate (up to speed limit, but let's assume distance control handles gap closing too)
        # But if we are too close (error < 0), we MUST decelerate.
        
        # Let's assume PID output is acceleration
        acc = pid.compute(error, DT)
        acc = max(MAX_DECEL, min(acc, MAX_ACCEL))
        
        ego_speed += acc * DT
        ego_speed = max(0, ego_speed)
        
        # Update distance
        # dist_new = dist_old + (v_lead - v_ego) * dt
        distance += (lead_speed - ego_speed) * DT
        
        times.append(t)
        dist_errors.append(error)
        t += DT
        
    return times, dist_errors

def calculate_dist_metrics(times, errors):
    # SS Error (last 5 seconds)
    final_avg = sum(errors[-50:]) / 50
    ss_error = abs(final_avg)
    return ss_error

def tune_dist_pid():
    best_score = float('inf')
    best_gains = (0.5, 0.0, 0.0)
    
    kps = [0.1, 0.3, 0.5, 0.8, 1.0]
    kis = [0.0, 0.01, 0.05, 0.1]
    kds = [0.0, 0.1, 0.5]
    
    for kp in kps:
        for ki in kis:
            for kd in kds:
                times, errors = simulate_distance_follow(kp, ki, kd)
                ss = calculate_dist_metrics(times, errors)
                
                # Constraint: SS < 2m
                if ss < 2.0:
                    score = ss
                    if score < best_score:
                        best_score = score
                        best_gains = (kp, ki, kd)
    return best_gains

if __name__ == "__main__":
    skp, ski, skd = tune_speed_pid()
    dkp, dki, dkd = tune_dist_pid()
    
    results = {
        'pid_speed': {'kp': skp, 'ki': ski, 'kd': skd},
        'pid_distance': {'kp': dkp, 'ki': dki, 'kd': dkd}
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)
    
    print("Tuning complete. Results saved.")
    print(results)

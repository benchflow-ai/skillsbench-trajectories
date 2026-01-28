import yaml
import numpy as np
from pid_controller import PIDController

def simulate_step_response(kp, ki, kd, target_speed, duration=150, dt=0.1):
    pid = PIDController(kp, ki, kd)
    speed = 0.0
    speeds = []
    accels = []
    times = np.arange(0, duration, dt)
    
    for t in times:
        error = target_speed - speed
        accel = pid.compute(error, dt)
        accel = max(-8.0, min(accel, 3.0))
        speed += accel * dt
        speed = max(0, speed)
        speeds.append(speed)
        accels.append(accel)
        
    return np.array(speeds), np.array(accels), times

def calculate_metrics(speeds, times, target_speed):
    # Rise time: time to go from 10% to 90% of target
    final_speed = speeds[-1]
    if final_speed < 0.9 * target_speed:
        return float('inf'), float('inf'), float('inf')
        
    idx_10 = np.where(speeds >= 0.1 * target_speed)[0][0]
    idx_90 = np.where(speeds >= 0.9 * target_speed)[0][0]
    rise_time = times[idx_90] - times[idx_10]
    
    # Overshoot
    max_speed = np.max(speeds)
    overshoot = (max_speed - target_speed) / target_speed * 100
    
    # Steady state error (last 10 seconds)
    sse = np.mean(np.abs(speeds[-100:] - target_speed))
    
    return rise_time, overshoot, sse

def tune_speed_pid():
    best_score = float('inf')
    best_gains = (0,0,0)
    
    # Coarse search
    for kp in [0.1, 0.5, 1.0, 2.0, 5.0]:
        for ki in [0.0, 0.01, 0.1, 0.5]:
            for kd in [0.0, 0.1, 0.5, 1.0]:
                speeds, _, times = simulate_step_response(kp, ki, kd, 30.0)
                rt, os, sse = calculate_metrics(speeds, times, 30.0)
                
                # Constraints
                if rt > 10.0 or os > 5.0 or sse > 0.5:
                    continue
                    
                score = rt + os + sse*10
                if score < best_score:
                    best_score = score
                    best_gains = (kp, ki, kd)
                    
    return best_gains

def simulate_distance_response(kp, ki, kd, target_dist, duration=150, dt=0.1):
    # Simplified: Lead car constant speed, ego starts at correct speed but wrong distance
    pid = PIDController(kp, ki, kd)
    ego_speed = 30.0
    lead_speed = 30.0
    current_dist = 100.0 # Start far away
    target_dist = 30.0 * 1.5 + 10.0 # 55m
    
    dists = []
    times = np.arange(0, duration, dt)
    
    for t in times:
        error = current_dist - target_dist
        accel = pid.compute(error, dt)
        accel = max(-8.0, min(accel, 3.0))
        
        ego_speed += accel * dt
        ego_speed = max(0, ego_speed)
        current_dist += (lead_speed - ego_speed) * dt
        dists.append(current_dist)
        
    return np.array(dists), times

def tune_distance_pid():
    best_score = float('inf')
    best_gains = (0,0,0)
    target_dist = 55.0
    
    for kp in [0.1, 0.3, 0.5, 0.8, 1.0]:
        for ki in [0.0, 0.01, 0.05]:
            for kd in [0.0, 0.1, 0.5]:
                dists, times = simulate_distance_response(kp, ki, kd, target_dist)
                
                sse = np.mean(np.abs(dists[-100:] - target_dist))
                
                # Simple score: minimize SSE and ensure stability
                if sse > 2.0:
                    continue
                    
                score = sse
                if score < best_score:
                    best_score = score
                    best_gains = (kp, ki, kd)
    return best_gains

if __name__ == '__main__':
    s_kp, s_ki, s_kd = tune_speed_pid()
    d_kp, d_ki, d_kd = tune_distance_pid()
    
    results = {
        'pid_speed': {'kp': float(s_kp), 'ki': float(s_ki), 'kd': float(s_kd)},
        'pid_distance': {'kp': float(d_kp), 'ki': float(d_ki), 'kd': float(d_kd)}
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)
    print('Tuning complete:', results)

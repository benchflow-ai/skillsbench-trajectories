import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def simulate_speed_response(kp, ki, kd):
    # Setup
    config = {
        'vehicle': {'max_acceleration': 3.0, 'max_deceleration': -8.0},
        'acc_settings': {
            'set_speed': 30.0, 'time_headway': 1.5, 'min_distance': 10.0, 'emergency_ttc_threshold': 3.0
        },
        'pid_speed': {'kp': kp, 'ki': ki, 'kd': kd},
        'pid_distance': {'kp': 0, 'ki': 0, 'kd': 0}
    }
    acc = AdaptiveCruiseControl(config)
    
    dt = 0.1
    time = 0.0
    duration = 50.0
    ego_speed = 0.0
    target_speed = 30.0
    
    times = []
    speeds = []
    
    while time < duration:
        acc_cmd, mode, _ = acc.compute(ego_speed, None, None, dt)
        ego_speed += acc_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
        times.append(time)
        speeds.append(ego_speed)
        time += dt
        
    speeds = np.array(speeds)
    times = np.array(times)
    
    # Metrics
    target_90 = 0.9 * target_speed
    if np.any(speeds >= target_90):
        idx_90 = np.argmax(speeds >= target_90)
        rise_time = times[idx_90]
    else:
        rise_time = 999.0
    
    max_speed = np.max(speeds)
    overshoot = (max_speed - target_speed) / target_speed * 100 
    
    ss_error = np.mean(np.abs(speeds[-100:] - target_speed))
    
    return rise_time, overshoot, ss_error

def simulate_distance_response(kp, ki, kd, speed_gains):
    # Combined Scenario: 
    # 1. Catch up (mild)
    # 2. Hard Brake (Lead stops)
    
    config = {
        'vehicle': {'max_acceleration': 3.0, 'max_deceleration': -8.0},
        'acc_settings': {
            'set_speed': 30.0, 'time_headway': 1.5, 'min_distance': 10.0, 'emergency_ttc_threshold': 3.0
        },
        'pid_speed': speed_gains,
        'pid_distance': {'kp': kp, 'ki': ki, 'kd': kd}
    }
    acc = AdaptiveCruiseControl(config)
    
    dt = 0.1
    time = 0.0
    duration = 100.0
    
    ego_speed = 30.0 
    ego_pos = 0.0
    
    lead_speed = 30.0
    lead_pos = 60.0 # 1.5*30 + 10 = 55. We are at 60 (safe).
    
    min_dist_observed = float('inf')
    dist_errors = []
    
    # 0-10s: Steady
    # 10-20s: Lead decelerates to 10 m/s
    # 20-50s: Constant 10 m/s
    
    while time < duration:
        # Lead Dynamics
        if 10.0 <= time < 15.0:
            lead_speed -= 4.0 * dt # Decel 4 m/s^2 (Hard) to 10 m/s
            lead_speed = max(10.0, lead_speed)
        
        lead_pos += lead_speed * dt
        
        distance = lead_pos - ego_pos
        min_dist_observed = min(min_dist_observed, distance)
        
        if distance <= 0:
            # Collision
            return 999.0, -999.0 # Fail

        acc_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        ego_speed += acc_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt
        
        if dist_err is not None:
            dist_errors.append(dist_err)
        
        time += dt

    final_errors = dist_errors[-100:]
    ss_error = np.mean(np.abs(final_errors))
    
    return ss_error, min_dist_observed

def tune():
    best_speed_gains = None
    
    print("Tuning Speed PID...")
    found_speed = False
    # Speed Loop
    for kp in [0.2, 0.4, 0.6, 0.8, 1.0]:
        for ki in [0.0, 0.01, 0.1]:
            for kd in [0.0, 0.1]:
                rt, os, ss = simulate_speed_response(kp, ki, kd)
                if rt < 10.0 and os < 5.0 and ss < 0.5:
                    best_speed_gains = {'kp': float(kp), 'ki': float(ki), 'kd': float(kd)}
                    # Prefer higher Kp for responsiveness if valid
                    # Keep searching? No, first match is okay for now.
                    # But actually we want minimal overshoot.
                    found_speed = True
                    break
            if found_speed: break
        if found_speed: break
    
    if not best_speed_gains:
        best_speed_gains = {'kp': 0.5, 'ki': 0.0, 'kd': 0.0}

    print(f"Selected Speed Gains: {best_speed_gains}")

    print("Tuning Distance PID...")
    best_dist_gains = None
    found_dist = False
    
    # Distance Loop
    # We need stronger Kp to handle braking.
    for kp in [0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0]:
        for ki in [0.0, 0.01, 0.05, 0.1]:
            for kd in [0.0, 0.5, 1.0, 2.0]: # Kd helps braking
                ss_err, min_d = simulate_distance_response(kp, ki, kd, best_speed_gains)
                # Targets: SS Error < 2m, Min Dist > 5m
                if ss_err < 2.0 and min_d > 5.0:
                    best_dist_gains = {'kp': float(kp), 'ki': float(ki), 'kd': float(kd)}
                    print(f"Dist Gain Found: {best_dist_gains} (SS={ss_err:.2f}, MinD={min_d:.2f})")
                    found_dist = True
                    break
            if found_dist: break
        if found_dist: break
        
    if not best_dist_gains:
         print("Failed to find distance gains, using fallback")
         best_dist_gains = {'kp': 0.6, 'ki': 0.01, 'kd': 1.0}

    # Save
    results = {
        'pid_speed': best_speed_gains,
        'pid_distance': best_dist_gains
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)
    
    print("Saved tuning_results.yaml")

if __name__ == "__main__":
    tune()
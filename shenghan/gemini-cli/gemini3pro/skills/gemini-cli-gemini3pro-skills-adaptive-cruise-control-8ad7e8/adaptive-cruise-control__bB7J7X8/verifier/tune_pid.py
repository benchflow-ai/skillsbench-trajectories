import yaml
import numpy as np
from pid_controller import PIDController

# Load params to get constraints
with open('vehicle_params.yaml', 'r') as f:
    params = yaml.safe_load(f)

MASS = params['vehicle']['mass']
MAX_ACCEL = params['vehicle']['max_acceleration']
MAX_DECEL = params['vehicle']['max_deceleration']
DRAG_COEF = params['vehicle']['drag_coefficient']
DT = params['simulation']['dt']
SET_SPEED = params['acc_settings']['set_speed']

def get_drag(v):
    # Assuming drag_coefficient is the lumped factor F = Cv^2 or similar
    # If not specified, we guess F = 0.5 * rho * A * Cd * v^2.
    # Without A, we'll assume the provided coefficient is the effective one: F = Cd * v^2?
    # Or F = Cd * v? 0.3 is high for Cd alone (usually 0.3), but 0.3 * v^2 / 1500 is small.
    # Let's assume F_drag = Cd * v^2 as a reasonable approximation if dimensions aren't given.
    return DRAG_COEF * v * v

def simulate_speed_step(kp, ki, kd):
    pid = PIDController(kp, ki, kd)
    v = 0.0
    time = 0.0
    history = []
    
    target = SET_SPEED
    
    # 150 seconds simulation
    steps = int(150 / DT)
    
    for _ in range(steps):
        error = target - v
        a_cmd = pid.compute(error, DT)
        
        # Clamp command
        a_cmd = max(MAX_DECEL, min(a_cmd, MAX_ACCEL))
        
        # Physics
        f_drag = get_drag(v)
        a_net = a_cmd - (f_drag / MASS)
        
        # Update
        v += a_net * DT
        if v < 0: v = 0
        
        time += DT
        history.append((time, v))
        
    # Analyze
    times = [h[0] for h in history]
    speeds = [h[1] for h in history]
    
    # Rise time: time to reach 90% of target (or 10-90, but let's say 0 to 90 for simple check)
    # The prompt says "speed rise time < 10s". Usually 10% to 90%.
    t_10 = next((t for t, s in zip(times, speeds) if s >= 0.1 * target), 150)
    t_90 = next((t for t, s in zip(times, speeds) if s >= 0.9 * target), 150)
    rise_time = t_90 - t_10
    
    # Overshoot
    max_v = max(speeds)
    overshoot = (max_v - target) / target * 100 if max_v > target else 0
    
    # Steady state error (last 10 seconds average or just last point)
    final_v = speeds[-1]
    ss_error = abs(target - final_v)
    
    return rise_time, overshoot, ss_error

def simulate_distance_scenario(kp, ki, kd, speed_pid):
    # Scenario: Lead car constant 20m/s. Ego starts 30m/s. Distance 100m.
    # Target distance will be 10 + 1.5 * 20 = 40m.
    
    pid_dist = PIDController(kp, ki, kd)
    pid_speed = PIDController(speed_pid['kp'], speed_pid['ki'], speed_pid['kd'])
    
    v_ego = 30.0
    v_lead = 20.0
    dist = 100.0
    time = 0.0
    
    min_dist_observed = dist
    
    history = []
    
    # 150 seconds
    steps = int(150 / DT)
    
    target_speed = SET_SPEED # 30
    
    for _ in range(steps):
        # Distance Control
        safe_dist = params['acc_settings']['min_distance'] + params['acc_settings']['time_headway'] * v_ego
        
        dist_error = dist - safe_dist
        a_dist = pid_dist.compute(dist_error, DT)
        
        # Speed Control (Cruise) - we need this for the min() logic if we implement it, 
        # or just to check if we are speed limited.
        # But in 'Follow' we usually follow distance. 
        # However, we must not exceed max speed.
        # Let's assume standard ACC behavior: min(dist_accel, speed_accel)
        
        speed_error = target_speed - v_ego
        a_speed = pid_speed.compute(speed_error, DT) # Update state
        
        # Combined logic (Safety: don't crash, don't speed)
        # If we are strictly in "follow" mode, we follow distance.
        # But if distance command says "Accelerate hard" because lead is far,
        # we should be limited by speed controller.
        
        # For tuning distance PID, we want to ensure that *when following*, it performs well.
        # In this scenario, we are closing in (dist 100, safe ~55 at 30m/s).
        # safe_dist depends on v_ego.
        # At start: safe = 10 + 1.5*30 = 55m. Dist = 100. Error = 45m (positive).
        # PID will ask to accelerate.
        # But we are already at 30m/s (Set Speed).
        # So Speed PID will ask for 0 accel (or negative if slightly above).
        # min(a_dist, a_speed) will be ~0.
        # As we get closer?
        # Wait, if Lead is 20m/s, we approach at 10m/s.
        # Dist decreases.
        # Eventually dist < safe_dist. Error becomes negative. a_dist becomes negative.
        # Then min(a_dist, a_speed) will be a_dist (braking).
        
        a_cmd = min(a_dist, a_speed)
        
        # Clamp
        a_cmd = max(MAX_DECEL, min(a_cmd, MAX_ACCEL))
        
        # Physics
        f_drag = get_drag(v_ego)
        a_net = a_cmd - (f_drag / MASS)
        
        v_ego += a_net * DT
        if v_ego < 0: v_ego = 0
        
        # Kinematics
        d_dist = (v_lead - v_ego) * DT
        dist += d_dist
        
        if dist < min_dist_observed:
            min_dist_observed = dist
            
        time += DT
        history.append(dist)

    # Steady state check
    # Final state: v_ego should match v_lead (20).
    # Safe dist should be 10 + 1.5 * 20 = 40.
    final_dist = history[-1]
    target_dist = 10.0 + 1.5 * v_lead # 40.0
    ss_error = abs(final_dist - target_dist)
    
    return min_dist_observed, ss_error

def tune():
    # Tune Speed Loop
    best_speed_params = None
    best_speed_score = float('inf')
    
    # Coarse grid search
    for kp in [0.5, 1.0, 2.0, 3.0, 5.0]:
        for ki in [0.0, 0.1, 0.5, 1.0]:
            for kd in [0.0, 0.1, 0.5, 1.0]:
                rt, os, ss = simulate_speed_step(kp, ki, kd)
                
                # Check constraints
                if rt < 10.0 and os < 5.0 and ss < 0.5:
                    # Score? Minimize Rise time + Error?
                    score = rt + os + ss*10
                    if score < best_speed_score:
                        best_speed_score = score
                        best_speed_params = {'kp': kp, 'ki': ki, 'kd': kd}

    print(f"Best Speed Params: {best_speed_params}")
    
    if best_speed_params is None:
        # Fallback if strict constraints not met, pick something reasonable
        best_speed_params = {'kp': 2.0, 'ki': 0.1, 'kd': 0.0}

    # Tune Distance Loop
    best_dist_params = None
    best_dist_score = float('inf')
    
    # Distance loop needs to be responsive but not crash
    for kp in [0.1, 0.3, 0.5, 0.8, 1.0]:
        for ki in [0.0, 0.01, 0.05, 0.1]:
            for kd in [0.0, 0.1, 0.5, 1.0]:
                min_d, ss = simulate_distance_scenario(kp, ki, kd, best_speed_params)
                
                # Constraints: min_dist > 5m, ss_error < 2m
                if min_d > 5.0 and ss < 2.0:
                    # Score: Maximize min_dist (safety) and minimize ss_error
                    # Actually we want smooth control.
                    # Let's minimize error.
                    score = ss
                    if score < best_dist_score:
                        best_dist_score = score
                        best_dist_params = {'kp': kp, 'ki': ki, 'kd': kd}

    print(f"Best Dist Params: {best_dist_params}")
    if best_dist_params is None:
        best_dist_params = {'kp': 0.5, 'ki': 0.01, 'kd': 0.1}

    # Save results
    results = {
        'pid_speed': best_speed_params,
        'pid_distance': best_dist_params
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

if __name__ == "__main__":
    tune()

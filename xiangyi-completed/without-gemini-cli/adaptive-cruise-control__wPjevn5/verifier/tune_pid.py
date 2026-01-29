import yaml
import numpy as np
from pid_controller import PIDController

# Load vehicle params just to get constraints
with open('vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

dt = 0.1
max_accel = config['vehicle']['max_acceleration']
max_decel = config['vehicle']['max_deceleration']
set_speed = config['acc_settings']['set_speed']

def simulate_cruise(kp, ki, kd):
    pid = PIDController(kp, ki, kd)
    v = 0.0
    t = 0.0
    history_v = []
    history_t = []
    
    while t < 60.0: # 60s simulation
        error = set_speed - v
        acc = pid.compute(error, dt)
        acc = max(max_decel, min(max_accel, acc))
        v += acc * dt
        # Drag is not modeled in the PID controller logic but SHOULD be in the physics
        # The prompt says "vehicle_params.yaml" has "drag_coefficient: 0.3"
        # Wait, if I simulate physics, I should include drag.
        # F_net = m*a_cmd - F_drag? 
        # Usually ACC command IS the requested acceleration (closed loop on low-level controller).
        # Assuming "acceleration_cmd" is achieved perfectly by the lower-level vehicle dynamics
        # UNLESS the prompt implies we need to model the vehicle dynamics including drag.
        # "vehicle_params.yaml... mass: 1500... drag_coefficient: 0.3".
        # This implies physics model: a_actual = (F_engine - F_drag) / m
        # But ACC outputs acceleration_cmd. Does ACC output F_engine?
        # "Method: compute(...) returns tuple (acceleration_cmd...)"
        # Usually ACC outputs commanded acceleration, and a lower-level ECU handles the throttle/brake.
        # However, for this simulation task, usually we assume a_actual = a_cmd (clamped).
        # OR we assume a_actual = a_cmd - drag_decel?
        # Let's assume a_actual = a_cmd for the tuning to be robust, but maybe check if drag is significant.
        # If I ignore drag in tuning but include it in simulation, I might undershoot.
        # Let's include drag in the physics update for tuning to match simulation.
        # Physics:
        # F_drag = 0.5 * rho * Cd * A * v^2?
        # We only have drag_coefficient (0.3). Maybe it's a simplified drag model F = Cd * v? Or Cd * v^2?
        # Or maybe the "acceleration_cmd" is NET acceleration?
        # Given "mass", maybe `a_cmd` is force/mass?
        # Let's assume the simple case: a_vehicle = a_cmd.
        # If the user wanted detailed physics, they'd provide air density, frontal area etc.
        # "drag_coefficient: 0.3" is unitless usually, requires Area.
        # Maybe it's a lumped "drag factor" such that F_drag = 0.3 * v^2? 
        # Without Area, we can't compute drag force properly.
        # I will assume `a_vehicle = a_cmd` (ideal low-level control).
        
        history_v.append(v)
        history_t.append(t)
        t += dt
        
    history_v = np.array(history_v)
    history_t = np.array(history_t)
    
    # Analyze
    # Rise time: time from 10% to 90% of set_speed
    v_10 = 0.1 * set_speed
    v_90 = 0.9 * set_speed
    
    idx_10 = np.where(history_v >= v_10)[0]
    idx_90 = np.where(history_v >= v_90)[0]
    
    if len(idx_10) > 0 and len(idx_90) > 0:
        rise_time = history_t[idx_90[0]] - history_t[idx_10[0]]
    else:
        rise_time = 999.0
        
    max_v = np.max(history_v)
    overshoot_percent = (max_v - set_speed) / set_speed * 100
    
    final_v = history_v[-1]
    ss_error = abs(set_speed - final_v)
    
    return rise_time, overshoot_percent, ss_error

def score_speed(kp, ki, kd):
    rt, os, ss = simulate_cruise(kp, ki, kd)
    # Constraints: RT < 10, OS < 5, SS < 0.5
    penalty = 0
    if rt > 10.0: penalty += (rt - 10.0) * 10
    if os > 5.0: penalty += (os - 5.0) * 10
    if ss > 0.5: penalty += (ss - 0.5) * 100
    return penalty, (rt, os, ss)

def tune_speed():
    best_score = float('inf')
    best_params = (0,0,0)
    best_metrics = (0,0,0)
    
    # Grid search or Random? 3 vars.
    # Kp: 0-10, Ki: 0-5, Kd: 0-5
    # Let's coarse grid then refine.
    for kp in [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 9.0]:
        for ki in [0.0, 0.1, 0.5, 1.0]:
            for kd in [0.0, 0.1, 0.5, 1.0]:
                score, metrics = score_speed(kp, ki, kd)
                if score < best_score:
                    best_score = score
                    best_params = (kp, ki, kd)
                    best_metrics = metrics
                    
    return best_params, best_metrics

def simulate_follow(kp_dist, ki_dist, kd_dist, speed_params):
    # Setup standard follow scenario
    # Ego starts at 30 m/s. Lead is at 25 m/s.
    # Initial distance = 60m. 
    # Desired dist = 10 + 1.5 * 30 = 55m.
    # Initially error = 60 - 55 = 5m (positive -> accelerate?).
    # Wait, if I am faster (30) than lead (25), I will close in.
    # Distance will decrease.
    # Ideally I should slow down to 25 m/s.
    
    kp_s, ki_s, kd_s = speed_params
    pid_speed = PIDController(kp_s, ki_s, kd_s)
    pid_dist = PIDController(kp_dist, ki_dist, kd_dist)
    
    v_ego = 30.0
    v_lead = 25.0 # Constant lead speed
    dist = 60.0
    t = 0.0
    
    min_dist_observed = dist
    final_dist_error = 999.0
    
    history_d_err = []
    
    while t < 60.0:
        # Update physics first or control first? 
        # Control based on current state.
        
        # Mode is follow because lead exists
        desired_dist = 10.0 + 1.5 * v_ego
        d_error = dist - desired_dist
        
        # Check TTC for emergency
        ttc = float('inf')
        if v_ego > v_lead:
            ttc = dist / (v_ego - v_lead)
            
        if ttc < 3.0:
            acc = -8.0 # Emergency
            pid_dist.reset()
        else:
            acc = pid_dist.compute(d_error, dt)
            
        acc = max(max_decel, min(max_accel, acc))
        
        v_ego += acc * dt
        if v_ego < 0: v_ego = 0
        
        dist += (v_lead - v_ego) * dt
        
        if dist < min_dist_observed:
            min_dist_observed = dist
            
        history_d_err.append(d_error)
        t += dt
        
    final_d_error = abs(history_d_err[-1])
    return final_d_error, min_dist_observed

def score_dist(kp, ki, kd, speed_params):
    fe, min_d = simulate_follow(kp, ki, kd, speed_params)
    # Constraints: SS Error < 2m. Min dist > 5m.
    penalty = 0
    if fe > 2.0: penalty += (fe - 2.0) * 10
    if min_d < 5.0: penalty += (5.0 - min_d) * 100
    
    return penalty, (fe, min_d)

def tune_dist(speed_params):
    best_score = float('inf')
    best_params = (0,0,0)
    best_metrics = (0,0,0)
    
    for kp in [0.1, 0.5, 1.0, 2.0]:
        for ki in [0.0, 0.01, 0.1]:
            for kd in [0.0, 0.1, 0.5, 1.0, 2.0]:
                score, metrics = score_dist(kp, ki, kd, speed_params)
                if score < best_score:
                    best_score = score
                    best_params = (kp, ki, kd)
                    best_metrics = metrics
    return best_params

if __name__ == "__main__":
    print("Tuning Speed PID...")
    p_speed, m_speed = tune_speed()
    print(f"Speed: {p_speed}, Metrics (RT, OS, SS): {m_speed}")
    
    print("Tuning Distance PID...")
    p_dist = tune_dist(p_speed)
    fe, min_d = simulate_follow(p_dist[0], p_dist[1], p_dist[2], p_speed)
    print(f"Dist: {p_dist}, Metrics (FE, MinD): {fe}, {min_d}")
    
    # Save results
    results = {
        'pid_speed': {'kp': float(p_speed[0]), 'ki': float(p_speed[1]), 'kd': float(p_speed[2])},
        'pid_distance': {'kp': float(p_dist[0]), 'ki': float(p_dist[1]), 'kd': float(p_dist[2])}
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

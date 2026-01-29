
import yaml
import copy
import math
from pid_controller import PIDController

# Load config
with open('vehicle_params.yaml', 'r') as f:
    base_config = yaml.safe_load(f)

dt = base_config['simulation']['dt']
max_accel = base_config['vehicle']['max_acceleration']
max_decel = base_config['vehicle']['max_deceleration']
set_speed = base_config['acc_settings']['set_speed']

def run_speed_simulation(kp, ki, kd):
    pid = PIDController(kp, ki, kd, max_decel, max_accel)
    
    time = 0.0
    speed = 0.0
    
    times = []
    speeds = []
    
    # 60 seconds simulation
    steps = int(60 / dt)
    
    for _ in range(steps):
        times.append(time)
        speeds.append(speed)
        
        error = set_speed - speed
        accel = pid.compute(error, dt)
        
        # Physics update with Drag
        # F_drag = 0.5 * rho * A * Cd * v^2
        # Assume rho=1.225, A=2.5
        drag_force = 0.5 * 1.225 * 2.5 * base_config['vehicle']['drag_coefficient'] * (speed ** 2)
        drag_decel = drag_force / base_config['vehicle']['mass']
        
        net_accel = accel - drag_decel
        speed += net_accel * dt
        speed = max(0.0, speed)
        time += dt
        
    return times, speeds

def calculate_speed_metrics(times, speeds, target):
    # Rise time (10% to 90%)
    t10 = None
    t90 = None
    max_speed = 0.0
    
    final_avg = sum(speeds[-50:]) / 50.0 # Last 5 seconds (50 steps)
    ss_error = abs(target - final_avg)
    
    for t, v in zip(times, speeds):
        if v > max_speed:
            max_speed = v
        
        if t10 is None and v >= 0.1 * target:
            t10 = t
        if t90 is None and v >= 0.9 * target:
            t90 = t
            
    rise_time = float('inf')
    if t10 is not None and t90 is not None:
        rise_time = t90 - t10
        
    overshoot = 0.0
    if max_speed > target:
        overshoot = (max_speed - target) / target * 100.0
        
    return rise_time, overshoot, ss_error

def tune_speed_pid():
    print("Tuning Speed PID...")
    best_score = float('inf')
    best_params = (0.0, 0.0, 0.0)
    
    # Grid search - optimized ranges based on experience
    kps = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    kis = [0.0, 0.01, 0.05, 0.1, 0.2]
    kds = [0.0, 0.1, 0.5, 1.0]
    
    valid_params = []

    for kp in kps:
        for ki in kis:
            for kd in kds:
                times, speeds = run_speed_simulation(kp, ki, kd)
                rt, os, sse = calculate_speed_metrics(times, speeds, set_speed)
                
                # Check constraints
                # rise time < 10s
                # overshoot < 5%
                # ss error < 0.5 m/s
                
                valid = True
                if rt > 10.0: valid = False
                if os > 5.0: valid = False
                if sse > 0.5: valid = False
                
                if valid:
                    # Score: lower is better. Prefer lower overshoot and SSE.
                    score = os + sse * 10 + rt * 0.1
                    if score < best_score:
                        best_score = score
                        best_params = (kp, ki, kd)
                    valid_params.append((kp, ki, kd, rt, os, sse))

    print(f"Best Speed Params: {best_params}")
    return best_params

def run_distance_simulation(kp_dist, ki_dist, kd_dist):
    # Test scenario: Following a lead vehicle
    # Lead moves at constant 20 m/s.
    # Ego starts at 25 m/s, distance 50m.
    # Safe distance for 20 m/s is 20*1.5 + 10 = 40m.
    # But wait, ego safe distance depends on ego speed.
    # If ego settles at 20 m/s, safe distance = 40m.
    # Current distance 50m. Ego is faster, so it will close in.
    
    pid = PIDController(kp_dist, ki_dist, kd_dist, max_decel, max_accel)
    
    lead_speed = 20.0
    ego_speed = 25.0
    distance = 50.0
    time = 0.0
    
    dists = []
    
    steps = int(60 / dt)
    
    for _ in range(steps):
        # Calculate safe distance based on EGO speed
        safe_dist = ego_speed * base_config['acc_settings']['time_headway'] + base_config['acc_settings']['min_distance']
        
        error = distance - safe_dist
        
        # We only test distance PID here, assuming we are in Follow mode
        accel = pid.compute(error, dt)
        accel = max(max_decel, min(accel, max_accel))
        
        # Physics with drag
        drag_force = 0.5 * 1.225 * 2.5 * base_config['vehicle']['drag_coefficient'] * (ego_speed ** 2)
        drag_decel = drag_force / base_config['vehicle']['mass']
        
        net_accel = accel - drag_decel
        ego_speed += net_accel * dt
        ego_speed = max(0.0, ego_speed)
        
        # Kinematics
        relative_speed = ego_speed - lead_speed
        distance -= relative_speed * dt
        
        dists.append(distance)
        time += dt
        
    return dists, ego_speed

def calculate_distance_metrics(dists, final_ego_speed):
    # Target distance depends on final settled speed
    # Ideally ego speed matches lead speed (20 m/s)
    # Target dist = 20 * 1.5 + 10 = 40.0
    
    target_dist = 20.0 * base_config['acc_settings']['time_headway'] + base_config['acc_settings']['min_distance']
    
    final_avg_dist = sum(dists[-50:]) / 50.0
    ss_error = abs(final_avg_dist - target_dist)
    
    # Also check stability - min distance should not be too small (safety)
    min_dist = min(dists)
    
    return ss_error, min_dist

def tune_distance_pid():
    print("Tuning Distance PID...")
    best_score = float('inf')
    best_params = (0.0, 0.0, 0.0)
    
    kps = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5]
    kis = [0.0, 0.01, 0.05, 0.1]
    kds = [0.0, 0.1, 0.5, 1.0] # Distance control often benefits from D to predict closing rate
    
    for kp in kps:
        for ki in kis:
            for kd in kds:
                dists, final_speed = run_distance_simulation(kp, ki, kd)
                sse, min_d = calculate_distance_metrics(dists, final_speed)
                
                # Constraints
                # SS error < 2m
                # Min distance > 5m (safety buffer)
                
                valid = True
                if sse > 2.0: valid = False
                if min_d < 5.0: valid = False
                
                if valid:
                    # Score: Minimize SSE
                    score = sse
                    if score < best_score:
                        best_score = score
                        best_params = (kp, ki, kd)
                        
    print(f"Best Distance Params: {best_params}")
    return best_params

if __name__ == "__main__":
    sp_kp, sp_ki, sp_kd = tune_speed_pid()
    dist_kp, dist_ki, dist_kd = tune_distance_pid()
    
    results = {
        'pid_speed': {
            'kp': float(sp_kp),
            'ki': float(sp_ki),
            'kd': float(sp_kd)
        },
        'pid_distance': {
            'kp': float(dist_kp),
            'ki': float(dist_ki),
            'kd': float(dist_kd)
        }
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)
    
    print("Results saved to tuning_results.yaml")

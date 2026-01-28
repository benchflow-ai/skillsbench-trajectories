import yaml
import copy
from pid_controller import PIDController

# Load base config
with open('vehicle_params.yaml', 'r') as f:
    base_config = yaml.safe_load(f)

dt = base_config['simulation']['dt']
max_accel = base_config['vehicle']['max_acceleration']
max_decel = base_config['vehicle']['max_deceleration']
set_speed = base_config['acc_settings']['set_speed']

def simulate_speed(kp, ki, kd):
    pid = PIDController(kp, ki, kd)
    speed = 0.0
    time = 0.0
    history = []
    
    for _ in range(int(50/dt)):
        error = set_speed - speed
        accel = pid.compute(error, dt)
        accel = max(max_decel, min(max_accel, accel))
        speed += accel * dt
        time += dt
        history.append(speed)
        
    # Metrics
    final_speed = history[-1]
    steady_error = abs(set_speed - final_speed)
    overshoot = (max(history) - set_speed) / set_speed if max(history) > set_speed else 0.0
    
    # Rise time (10% to 90%)
    t10 = next((i*dt for i, v in enumerate(history) if v >= 0.1*set_speed), 50.0)
    t90 = next((i*dt for i, v in enumerate(history) if v >= 0.9*set_speed), 50.0)
    rise_time = t90 - t10
    
    # Cost function
    # We want rise time < 10, overshoot < 5%, steady error < 0.5
    cost = 0.0
    if rise_time > 10.0: cost += 1000
    if overshoot > 0.05: cost += 1000
    if steady_error > 0.5: cost += 1000
    
    cost += rise_time * 1.0 + overshoot * 100 + steady_error * 10
    return cost, {'rise_time': rise_time, 'overshoot': overshoot, 'steady_error': steady_error}

def tune_speed():
    best_cost = float('inf')
    best_params = None
    
    kps = [0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0]
    kis = [0.0, 0.01, 0.05, 0.1, 0.2]
    kds = [0.0, 0.1, 0.5, 1.0]
    
    for kp in kps:
        for ki in kis:
            for kd in kds:
                cost, metrics = simulate_speed(kp, ki, kd)
                if cost < best_cost:
                    best_cost = cost
                    best_params = {'kp': kp, 'ki': ki, 'kd': kd}
    return best_params

def simulate_distance(kp, ki, kd):
    # Setup
    pid = PIDController(kp, ki, kd)
    
    # Scenario: Lead car at 20 m/s. Ego at 25 m/s. Distance starts at 50m.
    # Target distance = 10 + 1.5 * EgoSpeed.
    # Ego speed varies.
    
    ego_speed = 25.0
    lead_speed = 20.0
    distance = 50.0
    min_dist = base_config['acc_settings']['min_distance']
    time_headway = base_config['acc_settings']['time_headway']
    
    total_error = 0.0
    min_dist_observed = distance
    
    for _ in range(int(50/dt)):
        target_dist = min_dist + time_headway * ego_speed
        error = distance - target_dist
        
        accel = pid.compute(error, dt)
        accel = max(max_decel, min(max_accel, accel))
        
        ego_speed += accel * dt
        ego_speed = max(0.0, ego_speed)
        
        distance += (lead_speed - ego_speed) * dt
        
        total_error += abs(error)
        if distance < min_dist_observed:
            min_dist_observed = distance

    # Metrics
    steady_state_error = abs(distance - (min_dist + time_headway * ego_speed))
    
    cost = 0.0
    if min_dist_observed < 5.0: cost += 10000 # Crash/Unsafe
    if steady_state_error > 2.0: cost += 1000
    
    cost += total_error * 0.1 + steady_state_error * 10
    return cost

def tune_distance():
    best_cost = float('inf')
    best_params = None
    
    kps = [0.1, 0.3, 0.5, 0.8, 1.0]
    kis = [0.0, 0.01, 0.05]
    kds = [0.0, 0.1, 0.3, 0.5]
    
    for kp in kps:
        for ki in kis:
            for kd in kds:
                cost = simulate_distance(kp, ki, kd)
                if cost < best_cost:
                    best_cost = cost
                    best_params = {'kp': kp, 'ki': ki, 'kd': kd}
    return best_params

if __name__ == '__main__':
    print("Tuning Speed PID...")
    best_speed = tune_speed()
    print("Best Speed Params:", best_speed)
    
    print("Tuning Distance PID...")
    best_dist = tune_distance()
    print("Best Distance Params:", best_dist)
    
    results = {
        'pid_speed': best_speed,
        'pid_distance': best_dist
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

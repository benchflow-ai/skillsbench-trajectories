import yaml
import random
import copy
from pid_controller import PIDController

# Load vehicle params
with open('vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

DT = config['simulation']['dt']
MAX_ACCEL = config['vehicle']['max_acceleration']
MAX_DECEL = config['vehicle']['max_deceleration']
SET_SPEED = config['acc_settings']['set_speed']
TIME_HEADWAY = config['acc_settings']['time_headway']
MIN_DISTANCE = config['acc_settings']['min_distance']

def simulate_speed_response(kp, ki, kd, duration=60.0):
    controller = PIDController(kp, ki, kd, output_min=MAX_DECEL, output_max=MAX_ACCEL)
    speed = 0.0
    times = []
    speeds = []
    
    steps = int(duration / DT)
    for _ in range(steps):
        times.append(len(times) * DT)
        speeds.append(speed)
        
        error = SET_SPEED - speed
        accel = controller.compute(error, DT)
        
        speed += accel * DT
        speed = max(0.0, speed)
        
    return times, speeds

def evaluate_speed(kp, ki, kd):
    times, speeds = simulate_speed_response(kp, ki, kd)
    
    # Rise time (10% to 90%)
    t10 = next((t for t, v in zip(times, speeds) if v >= 0.1 * SET_SPEED), None)
    t90 = next((t for t, v in zip(times, speeds) if v >= 0.9 * SET_SPEED), None)
    rise_time = (t90 - t10) if (t10 is not None and t90 is not None) else 999.0
    
    # Overshoot
    max_speed = max(speeds)
    overshoot = (max_speed - SET_SPEED) / SET_SPEED * 100 if max_speed > SET_SPEED else 0.0
    
    # Steady state error (last 5 seconds)
    final_avg = sum(speeds[-50:]) / 50
    ss_error = abs(SET_SPEED - final_avg)
    
    # Constraints
    valid = True
    if rise_time >= 10.0: valid = False
    if overshoot >= 5.0: valid = False
    if ss_error >= 0.5: valid = False
    
    # Cost function (lower is better)
    cost = ss_error * 10 + overshoot + rise_time * 0.1
    if not valid:
        cost += 1000.0
        
    return cost, {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_error': ss_error,
        'valid': valid
    }

def simulate_distance_response(kp, ki, kd, duration=60.0):
    # Scenario: Lead vehicle at constant speed, Ego catches up
    # Ego starts at matched speed but far away? 
    # Or Lead decelerates?
    # Let's try: Lead const 20m/s. Ego starts 30m/s (catching up)
    # Target distance at 30m/s: 30*1.5 + 10 = 55m.
    # Start distance: 100m.
    
    controller = PIDController(kp, ki, kd, output_min=MAX_DECEL, output_max=MAX_ACCEL)
    
    lead_speed = 20.0
    ego_speed = 30.0 # Catching up
    distance = 100.0
    
    distances = []
    errors = []
    min_dist_observed = distance
    
    steps = int(duration / DT)
    for _ in range(steps):
        target_dist = ego_speed * TIME_HEADWAY + MIN_DISTANCE
        error = distance - target_dist
        
        # For distance control, error > 0 means too far -> Accelerate?
        # Wait, if distance (100) > target (55), error = 45. 
        # But we are approaching (ego > lead). We want to slow down to match speed eventually?
        # Actually, if we are far away, we want to maintain set_speed (cruise). 
        # Distance control only active when "following".
        # But here we are simulating PURE distance PID loop to tune it.
        # If we are far, PID should output positive accel to close gap? 
        # But we are already faster (30 vs 20).
        # The standard ACC logic: Min(SpeedControl, DistanceControl).
        # But here we assume we are in "Follow" mode.
        
        # Let's create a scenario where we MUST follow.
        # Lead: 20m/s. Ego: 20m/s. Distance: 20m.
        # Target: 20*1.5 + 10 = 40m.
        # Current distance (20) < Target (40). Too close!
        # Error = distance - target = -20.
        # We need negative accel (brake).
        # Controller output should be negative.
        # With Kp > 0, error -20 -> output -Kp*20. Correct.
        
        accel = controller.compute(error, DT)
        
        ego_speed += accel * DT
        ego_speed = max(0.0, ego_speed)
        
        # Kinematics
        relative_speed = ego_speed - lead_speed
        distance -= relative_speed * DT
        
        distances.append(distance)
        errors.append(error)
        if distance < min_dist_observed:
            min_dist_observed = distance
            
    return distances, errors, min_dist_observed

def evaluate_distance(kp, ki, kd):
    distances, errors, min_dist = simulate_distance_response(kp, ki, kd)
    
    # Steady state error (last 5s)
    final_error = sum([abs(e) for e in errors[-50:]]) / 50
    
    # Constraints
    valid = True
    if final_error >= 2.0: valid = False
    if min_dist <= 5.0: valid = False # Safety critical
    
    cost = final_error * 10
    if min_dist < 10.0: cost += (10.0 - min_dist) * 100 # Penalty for getting too close
    if not valid: cost += 1000.0
    
    return cost, {
        'ss_error': final_error,
        'min_dist': min_dist,
        'valid': valid
    }

def tune():
    best_speed = {'kp': 0, 'ki': 0, 'kd': 0, 'cost': float('inf')}
    best_dist = {'kp': 0, 'ki': 0, 'kd': 0, 'cost': float('inf')}
    
    print("Tuning Speed PID...")
    for _ in range(200):
        kp = random.uniform(0.1, 5.0) # Reduced range for better stability search initially
        ki = random.uniform(0.0, 2.0)
        kd = random.uniform(0.0, 2.0)
        
        cost, metrics = evaluate_speed(kp, ki, kd)
        if cost < best_speed['cost']:
            best_speed = {'kp': kp, 'ki': ki, 'kd': kd, 'cost': cost, 'metrics': metrics}
            
    print(f"Best Speed: {best_speed}")

    print("Tuning Distance PID...")
    for _ in range(200):
        kp = random.uniform(0.1, 5.0)
        ki = random.uniform(0.0, 1.0)
        kd = random.uniform(0.0, 2.0)
        
        cost, metrics = evaluate_distance(kp, ki, kd)
        if cost < best_dist['cost']:
            best_dist = {'kp': kp, 'ki': ki, 'kd': kd, 'cost': cost, 'metrics': metrics}

    print(f"Best Distance: {best_dist}")
    
    results = {
        'pid_speed': {k: float(v) for k, v in best_speed.items() if k in ['kp', 'ki', 'kd']},
        'pid_distance': {k: float(v) for k, v in best_dist.items() if k in ['kp', 'ki', 'kd']}
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

if __name__ == '__main__':
    tune()

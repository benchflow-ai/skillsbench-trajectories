import yaml
import sys
import copy
from acc_system import AdaptiveCruiseControl

# Load base config
with open('vehicle_params.yaml', 'r') as f:
    base_config = yaml.safe_load(f)

dt = base_config['simulation']['dt']

def simulate_speed(kp, ki, kd):
    config = copy.deepcopy(base_config)
    config['pid_speed']['kp'] = float(kp)
    config['pid_speed']['ki'] = float(ki)
    config['pid_speed']['kd'] = float(kd)
    
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    time = 0.0
    
    speeds = []
    times = []
    
    target = 30.0
    
    for _ in range(int(60/dt)): # 60 seconds
        accel, mode, _ = acc.compute(ego_speed, None, None, dt)
        ego_speed += accel * dt
        if ego_speed < 0: ego_speed = 0
        
        times.append(time)
        speeds.append(ego_speed)
        time += dt
        
    # Metrics
    # Rise time (0 to 90%)
    t_90 = None
    for t, v in zip(times, speeds):
        if v >= 0.9 * target:
            t_90 = t
            break
            
    if t_90 is None: t_90 = 999.0
    
    max_v = max(speeds)
    overshoot = (max_v - target) / target * 100
    final_v = speeds[-1]
    ss_error = abs(final_v - target)
    
    # Cost
    valid = True
    if t_90 > 10.0: valid = False
    if overshoot > 5.0: valid = False
    if ss_error > 0.5: valid = False
    
    # Simple cost function to prefer faster rise with low overshoot
    cost = t_90 + overshoot + ss_error * 10
    if not valid: cost += 1000.0
    
    return cost, valid, (t_90, overshoot, ss_error)

def simulate_distance(kp, ki, kd, speed_params):
    config = copy.deepcopy(base_config)
    config['pid_speed'] = speed_params
    config['pid_distance']['kp'] = float(kp)
    config['pid_distance']['ki'] = float(ki)
    config['pid_distance']['kd'] = float(kd)
    
    acc = AdaptiveCruiseControl(config)
    
    # Scenario: Lead at 20 m/s. Ego at 20 m/s but distance is 100m. Target distance ~ 40m.
    # Wait, simple regulation.
    # Let's try: Lead slows down?
    # Let's try: Lead constant 20 m/s. Ego starts 20 m/s at 100m. 
    # It should close the gap to (10 + 1.5*20) = 40m.
    
    lead_speed = 20.0
    ego_speed = 20.0
    distance = 100.0
    time = 0.0
    
    dists = []
    
    for _ in range(int(150/dt)):
        accel, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        # Physics
        ego_speed += accel * dt
        if ego_speed < 0: ego_speed = 0
        
        # Lead is constant 20
        # distance change = lead_speed - ego_speed
        distance += (lead_speed - ego_speed) * dt
        
        dists.append(distance)
        
    final_dist = dists[-1]
    target_dist = 10.0 + 1.5 * ego_speed # Should settle at 20m/s -> 40m
    
    ss_error = abs(final_dist - target_dist)
    min_d = min(dists)
    
    valid = True
    if ss_error > 2.0: valid = False
    if min_d < 5.0: valid = False
    
    cost = ss_error * 10 - min_d # minimize error, maximize safety buffer?
    # Actually just minimize error.
    cost = ss_error
    if not valid: cost += 1000.0
    
    return cost, valid, (ss_error, min_d)

# Tune Speed
best_speed_cost = float('inf')
best_speed_params = {'kp': 0.5, 'ki': 0.0, 'kd': 0.0}

print("Tuning Speed PID...")
# Coarse Grid
for kp in [0.5, 1.0, 2.0, 3.0, 5.0]:
    for ki in [0.0, 0.01, 0.05, 0.1, 0.5]:
        for kd in [0.0, 0.1, 0.5, 1.0]:
            cost, valid, metrics = simulate_speed(kp, ki, kd)
            if cost < best_speed_cost:
                best_speed_cost = cost
                best_speed_params = {'kp': kp, 'ki': ki, 'kd': kd}
                # print(f"New Best Speed: {best_speed_params}, Cost: {cost}, Metrics: {metrics}")

# Tune Distance
print("Tuning Distance PID...")
best_dist_cost = float('inf')
best_dist_params = {'kp': 0.5, 'ki': 0.0, 'kd': 0.0}

for kp in [0.1, 0.3, 0.5, 0.8, 1.0, 2.0]: # Distance loop usually slower
    for ki in [0.0, 0.001, 0.01, 0.05]:
        for kd in [0.0, 0.1, 0.5]:
            cost, valid, metrics = simulate_distance(kp, ki, kd, best_speed_params)
            if cost < best_dist_cost:
                best_dist_cost = cost
                best_dist_params = {'kp': kp, 'ki': ki, 'kd': kd}
                # print(f"New Best Dist: {best_dist_params}, Cost: {cost}, Metrics: {metrics}")

results = {
    'pid_speed': best_speed_params,
    'pid_distance': best_dist_params
}

print("Final Results:", results)

with open('tuning_results.yaml', 'w') as f:
    yaml.dump(results, f)

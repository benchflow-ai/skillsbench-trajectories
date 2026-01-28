
import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

# Load config
with open('vehicle_params.yaml', 'r') as f:
    base_config = yaml.safe_load(f)

# Load sensor data
df = pd.read_csv('sensor_data.csv')

def run_simulation(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d):
    config = base_config.copy()
    config['pid_speed'] = {'kp': kp_s, 'ki': ki_s, 'kd': kd_s}
    config['pid_distance'] = {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
    
    acc = AdaptiveCruiseControl(config)
    
    ego_speed = 0.0
    ego_pos = 0.0
    
    lead_pos = None
    
    dt = config['simulation']['dt']
    target_speed = config['acc_settings']['set_speed']
    
    speed_data = []
    distance_errors = []
    min_dist = float('inf')
    times = []
    
    for i, row in df.iterrows():
        time = row['time']
        rec_lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        rec_dist = row['distance'] if pd.notna(row['distance']) else None
        
        # Lead Position Logic
        if rec_lead_speed is not None and rec_dist is not None:
            if lead_pos is None:
                # Lead appears: spawn it at recorded distance relative to current ego pos
                lead_pos = ego_pos + rec_dist
            else:
                # Update lead pos based on lead speed
                lead_pos += rec_lead_speed * dt
        else:
            lead_pos = None
            
        # Calculate simulation distance
        distance = None
        if lead_pos is not None:
            distance = lead_pos - ego_pos
            min_dist = min(min_dist, distance)
            
        # ACC Compute
        accel, mode, dist_err = acc.compute(ego_speed, rec_lead_speed, distance, dt)
        
        # Physics update
        ego_speed += accel * dt
        ego_speed = max(0, ego_speed)
        ego_pos += ego_speed * dt
        
        # Metrics collection
        speed_data.append(ego_speed)
        times.append(time)
        if mode == 'follow' and dist_err is not None:
             # Store lead speed too for filtering
             current_lead_speed = rec_lead_speed if rec_lead_speed is not None else 0
             distance_errors.append((dist_err, current_lead_speed))

    # Metrics Calculation
    
    # 1. Rise Time (10-90%)
    t10 = None
    t90 = None
    for t, v in zip(times, speed_data):
        if t10 is None and v >= 0.1 * target_speed:
            t10 = t
        if t90 is None and v >= 0.9 * target_speed:
            t90 = t
            break
    rise_time = (t90 - t10) if (t10 is not None and t90 is not None) else 999
    
    # 2. Overshoot
    max_speed = max(speed_data)
    overshoot = ((max_speed - target_speed) / target_speed) * 100 if max_speed > target_speed else 0.0
    
    # 3. Speed SS Error (at 30m/s)
    # Check period before lead appears (t=30). Say t=20 to t=29.
    # If sim duration is short, this might fail.
    # Assuming lead appears at 30s.
    pre_lead_speeds = [v for t, v in zip(times, speed_data) if 20 <= t < 30]
    if pre_lead_speeds:
        speed_ss_err = abs(np.mean(pre_lead_speeds) - target_speed)
    else:
        speed_ss_err = 999
        
    # 4. Distance SS Error
    # Only consider errors when lead_speed < target_speed (followable)
    valid_errors = [e for e, lv in distance_errors if lv < (target_speed - 0.5)]
    
    if valid_errors:
        # Take last 50% of valid errors to represent "steady state" of that phase?
        # Or just mean of all valid errors if they are sparse.
        # Let's take mean of valid errors.
        avg_dist_err = np.mean(np.abs(valid_errors))
    else:
        avg_dist_err = 0.0 # No valid follow phase?
        
    return rise_time, overshoot, speed_ss_err, avg_dist_err, min_dist

# Optimization Loop
best_score = float('inf')
best_params = None

candidates = [
    # Kp_s, Ki_s, Kd_s, Kp_d, Ki_d, Kd_d
    # High Ki_d to close gap. High Kp_s to prevent overshoot.
    (1.0, 0.0, 1.0, 1.0, 0.2, 0.5),
    (1.5, 0.0, 2.0, 1.2, 0.3, 0.8),
    (2.0, 0.0, 2.0, 1.5, 0.4, 1.0),
    (0.8, 0.0, 1.0, 0.8, 0.25, 0.5),
    (1.2, 0.001, 1.5, 1.0, 0.3, 0.5),
    # Previous best for distance, but hardened for speed
    (0.5, 0.0, 0.5, 0.5, 0.3, 0.5),
    (0.8, 0.0, 0.8, 0.8, 0.4, 0.8)
]

best_params = candidates[0]
min_cost = float('inf')

print(f"{'Kp_s':<6} {'Ki_s':<6} {'Kd_s':<6} | {'Kp_d':<6} {'Ki_d':<6} {'Kd_d':<6} | {'Rise':<6} {'Over':<6} {'SpErr':<6} {'DstErr':<6} {'MinDst':<6}")

for params in candidates:
    rt, ov, se, de, md = run_simulation(*params)
    
    # Constraints
    valid = (rt < 10) and (ov < 5) and (se < 0.5) and (de < 2.0) and (md > 5.0)
    
    # Cost function
    cost = se + de + (ov/5.0) + (rt/10.0)
    if not valid:
        cost += 1000 # Penalty
        
    print(f"{params[0]:<6} {params[1]:<6} {params[2]:<6} | {params[3]:<6} {params[4]:<6} {params[5]:<6} | {rt:<6.2f} {ov:<6.2f} {se:<6.2f} {de:<6.2f} {md:<6.2f}")
    
    if cost < min_cost:
        min_cost = cost
        best_params = params

kp_s, ki_s, kd_s, kp_d, ki_d, kd_d = best_params

# Save results
results = {
    'pid_speed': {
        'kp': float(kp_s),
        'ki': float(ki_s),
        'kd': float(kd_s)
    },
    'pid_distance': {
        'kp': float(kp_d),
        'ki': float(ki_d),
        'kd': float(kd_d)
    }
}

with open('tuning_results.yaml', 'w') as f:
    yaml.dump(results, f)
    
print("Saved tuning_results.yaml")


import yaml
import csv
import os
from acc_system import AdaptiveCruiseControl

def simulate(pid_speed, pid_distance):
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    config['pid_speed'] = pid_speed
    config['pid_distance'] = pid_distance
    
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    ego_speed = 0.0
    current_distance = None
    
    times = []
    speeds = []
    dist_errors = []
    min_dist = float('inf')
    
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            orig_distance = float(row['distance']) if row['distance'] else None
            
            if lead_speed is not None and current_distance is None:
                current_distance = orig_distance
            elif lead_speed is not None and current_distance is not None:
                current_distance += (lead_speed - ego_speed) * dt
            else:
                current_distance = None
            
            accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, current_distance, dt)
            
            ego_speed += accel_cmd * dt
            ego_speed = max(0.0, ego_speed)
            
            times.append(t)
            speeds.append(ego_speed)
            if dist_err is not None:
                dist_errors.append(dist_err)
            if current_distance is not None:
                min_dist = min(min_dist, current_distance)
                
    cruise_speeds = [s for t, s in zip(times, speeds) if t < 30]
    rise_time = None
    for t, s in zip(times, speeds):
        if s >= 30.0 * 0.9:
            rise_time = t
            break
    
    max_speed_cruise = max(cruise_speeds) if cruise_speeds else 0
    overshoot = (max_speed_cruise - 30.0) / 30.0 if max_speed_cruise > 30.0 else 0
    sse_speed = abs(30.0 - cruise_speeds[-1]) if cruise_speeds else 0
    sse_distance = 0
    for t, err in zip(times, dist_errors):
        if t >= 70.0:
            sse_distance = abs(err)
            break
        
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'sse_speed': sse_speed,
        'sse_distance': sse_distance,
        'min_distance': min_dist
    }

def find_gains():
    # Search for speed
    best_speed = {'kp': 1.0, 'ki': 0.1, 'kd': 0.1}
    for kp in [0.5, 1.0, 2.0, 5.0]:
        for ki in [0.01, 0.05, 0.1]:
            res = simulate({'kp': kp, 'ki': ki, 'kd': 0.1}, {'kp': 0.5, 'ki': 0.01, 'kd': 0.1})
            if res['rise_time'] and res['rise_time'] < 10 and res['overshoot'] < 0.05 and res['sse_speed'] < 0.5:
                best_speed = {'kp': kp, 'ki': ki, 'kd': 0.1}
                break
        else: continue
        break

    # Search for distance
    best_dist = {'kp': 0.5, 'ki': 0.05, 'kd': 0.1}
    for kp in [0.5, 1.0, 2.0, 5.0, 8.0]:
        for ki in [0.1, 0.5, 1.0, 2.0]:
            res = simulate(best_speed, {'kp': kp, 'ki': ki, 'kd': 0.1})
            if res['sse_distance'] < 2.0 and res['min_distance'] > 5.0:
                best_dist = {'kp': kp, 'ki': ki, 'kd': 0.1}
                break
        else: continue
        break
        
    return best_speed, best_dist

speed_gains, dist_gains = find_gains()
best_gains = {'pid_speed': speed_gains, 'pid_distance': dist_gains}

best_res = simulate(best_gains['pid_speed'], best_gains['pid_distance'])
print("Final Metrics:")
print(best_res)
print("Gains:")
print(yaml.dump(best_gains))
with open('tuning_results.yaml', 'w') as f:
    yaml.dump(best_gains, f)

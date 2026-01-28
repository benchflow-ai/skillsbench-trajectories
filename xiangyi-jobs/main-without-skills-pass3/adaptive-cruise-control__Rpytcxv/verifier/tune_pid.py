import yaml
import csv
import math
import random
from acc_system import AdaptiveCruiseControl

def load_data(filename):
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed_csv': float(row['ego_speed']) if row['ego_speed'] else 0.0,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })
    return data

def run_simulation(data, config):
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    # Initialize state
    ego_speed = 0.0
    ego_pos = 0.0
    
    # Pre-calculate lead positions
    csv_ego_pos = 0.0
    lead_positions = [] 
    
    prev_time = data[0]['time']
    
    for i, row in enumerate(data):
        curr_time = row['time']
        if i > 0:
            d_time = curr_time - prev_time
            csv_ego_pos += row['ego_speed_csv'] * d_time
        
        if row['distance'] is not None:
            lead_pos = csv_ego_pos + row['distance']
            lead_positions.append({'time': curr_time, 'pos': lead_pos, 'speed': row['lead_speed']})
        else:
            lead_positions.append({'time': curr_time, 'pos': None, 'speed': None})
        
        prev_time = curr_time

    # Simulation Loop
    results = []
    
    for i, row in enumerate(data):
        t = row['time']
        
        # Determine current lead state
        lead_info = lead_positions[i]
        lead_pos = lead_info['pos']
        lead_v = lead_info['speed']
        
        # Calculate current distance relative to simulated ego
        if lead_pos is not None:
            dist = lead_pos - ego_pos
        else:
            dist = None
            
        # Run ACC
        acc_cmd, mode, dist_err = acc.compute(ego_speed, lead_v, dist, dt)
        
        # Update State
        ego_speed += acc_cmd * dt
        ego_speed = max(0.0, ego_speed) # No reverse
        ego_pos += ego_speed * dt
        
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'distance': dist,
            'mode': mode,
            'dist_err': dist_err
        })

    return results

def evaluate_speed(kp, ki, kd, base_config, data):
    config = base_config.copy()
    config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
    
    results = run_simulation(data, config)
    
    target = 30.0
    rise_time = None
    overshoot_val = 0.0
    ss_errors = []
    
    for r in results:
        t = r['time']
        v = r['ego_speed']
        
        if t > 30.0: break # Only care about first 30s
        
        if rise_time is None and v >= 0.9 * target:
            rise_time = t
            
        overshoot_val = max(overshoot_val, v - target)
        
        if t > 20.0:
            ss_errors.append(abs(target - v))
            
    if rise_time is None: rise_time = 30.0
    overshoot_pct = (overshoot_val / target) * 100
    avg_ss_error = sum(ss_errors) / len(ss_errors) if ss_errors else 10.0
    
    score = 0
    if rise_time > 10.0: score += 1000 + rise_time
    if overshoot_pct > 5.0: score += 1000 + overshoot_pct
    if avg_ss_error > 0.5: score += 1000 + avg_ss_error
    
    score += rise_time + overshoot_pct + avg_ss_error * 10
    
    return score, rise_time, overshoot_pct, avg_ss_error

def evaluate_distance(kp, ki, kd, speed_gains, base_config, data):
    config = base_config.copy()
    config['pid_speed'] = speed_gains
    config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}
    
    results = run_simulation(data, config)
    
    min_dist = float('inf')
    total_dist_err = 0
    count = 0
    
    # Analyze 30-150s
    for r in results:
        t = r['time']
        if t < 30.0: continue
        
        d = r['distance']
        if d is not None:
            min_dist = min(min_dist, d)
            
            target = max(10.0, r['ego_speed'] * 1.5)
            err = abs(d - target)
            total_dist_err += err
            count += 1
            
    avg_err = total_dist_err / count if count > 0 else 999
    
    score = 0
    if min_dist < 5.0: score += 100000 # Crash
    if avg_err > 2.0: score += 1000 + avg_err # Tolerance average
    
    score += avg_err
    
    return score, avg_err, min_dist

def main():
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)
        
    data = load_data('sensor_data.csv')
    
    # Speed Tuning
    print("Tuning Speed...")
    best_s_score = float('inf')
    best_s_gains = {'kp': 0.5, 'ki': 0.0, 'kd': 0.0}
    
    # Random search
    for _ in range(50):
        kp = random.uniform(0.1, 5.0)
        ki = random.uniform(0.0, 1.0)
        kd = random.uniform(0.0, 1.0)
        
        score, rt, ov, ss = evaluate_speed(kp, ki, kd, base_config, data)
        if score < best_s_score:
            best_s_score = score
            best_s_gains = {'kp': kp, 'ki': ki, 'kd': kd}
            print(f"Speed: {best_s_gains} S:{score:.1f} RT:{rt:.1f} OV:{ov:.1f}% SS:{ss:.2f}")

    # Distance Tuning
    print("Tuning Distance...")
    best_d_score = float('inf')
    best_d_gains = {'kp': 0.5, 'ki': 0.0, 'kd': 0.0}
    
    candidates_dist = []
    # Manual high Kd candidates
    candidates_dist.append((0.5, 0.01, 3.0))
    candidates_dist.append((0.5, 0.01, 5.0))
    candidates_dist.append((1.0, 0.01, 3.0))
    candidates_dist.append((0.8, 0.0, 4.0))
    
    # Random search
    for _ in range(50):
        kp = random.uniform(0.1, 2.0)
        ki = random.uniform(0.0, 0.5)
        kd = random.uniform(1.0, 8.0) # High Kd focus
        candidates_dist.append((kp, ki, kd))

    for kp, ki, kd in candidates_dist:
        score, avg_err, min_d = evaluate_distance(kp, ki, kd, best_s_gains, base_config, data)
        if score < best_d_score:
            best_d_score = score
            best_d_gains = {'kp': kp, 'ki': ki, 'kd': kd}
            print(f"Dist: {best_d_gains} S:{score:.1f} AvgErr:{avg_err:.2f} MinD:{min_d:.2f}")

    results = {
        'pid_speed': best_s_gains,
        'pid_distance': best_d_gains
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

if __name__ == "__main__":
    main()

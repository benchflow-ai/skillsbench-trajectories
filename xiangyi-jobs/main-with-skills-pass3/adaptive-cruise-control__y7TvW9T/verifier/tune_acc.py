import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def evaluate(speed_gains, dist_gains):
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load sensor data once
    data = pd.read_csv('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    acc.update_gains(speed_gains, dist_gains)
    
    dt = config['simulation']['dt']
    ego_speed = 0.0
    current_distance = None
    
    rise_time = None
    max_overshoot = 0.0
    min_dist = float('inf')
    dist_errors = []
    speed_errors = []
    
    for index, row in data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if not pd.isna(row['lead_speed']) else None
        raw_distance = row['distance'] if not pd.isna(row['distance']) else None
        
        if lead_speed is not None:
            if current_distance is None:
                current_distance = raw_distance
            else:
                current_distance += (lead_speed - ego_speed) * dt
            sim_distance = current_distance
        else:
            current_distance = None
            sim_distance = None
            
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, sim_distance, dt)
        
        ego_speed += accel_cmd * dt
        if ego_speed < 0: ego_speed = 0
        
        # Metrics
        if rise_time is None and ego_speed >= 0.9 * acc.set_speed:
            rise_time = time
            
        if ego_speed > acc.set_speed:
            overshoot = (ego_speed - acc.set_speed) / acc.set_speed * 100
            if overshoot > max_overshoot:
                max_overshoot = overshoot
                
        if sim_distance is not None:
            min_dist = min(min_dist, sim_distance)
            if mode == 'follow':
                dist_errors.append(abs(dist_err))
                
        if mode == 'cruise' and time > 20: # steady state speed check
            speed_errors.append(abs(acc.set_speed - ego_speed))
            
    avg_dist_error = np.mean(dist_errors) if dist_errors else 0.0
    avg_speed_error = np.mean(speed_errors) if speed_errors else 0.0
    
    # Check constraints
    valid = True
    if rise_time is None or rise_time > 10.0: valid = False
    if max_overshoot > 5.0: valid = False
    if avg_speed_error > 0.5: valid = False
    if avg_dist_error > 2.0: valid = False
    if min_dist < 5.0: valid = False
    
    score = avg_dist_error + avg_speed_error # Lower is better
    
    return valid, score, rise_time, max_overshoot, avg_speed_error, avg_dist_error, min_dist

def tune():
    # Ranges
    # Speed PID: needs to be aggressive enough for <10s rise time
    # Distance PID: needs to be stable
    
    best_score = float('inf')
    best_gains = None
    
    # Coarse search
    speed_kps = [0.5, 1.0, 2.0]
    speed_kis = [0.01, 0.05, 0.1]
    speed_kds = [0.0, 0.5, 1.0]
    
    dist_kps = [0.2, 0.5, 0.8]
    dist_kis = [0.01, 0.05]
    dist_kds = [0.0, 0.5]
    
    # To save time, we can try to tune speed first (using cruise part), then distance.
    # Or just iterate a small set of likely values.
    
    # Let's try a specific set that is likely to work based on control theory heuristics
    # For speed: Rise time < 10s -> needs reasonable Kp.
    # set_speed = 30. Max accel = 3. 30/3 = 10s (theoretical min time at max accel).
    # So we need to command max accel immediately. Error=30. Kp*30 >= 3 => Kp >= 0.1.
    # Let's try Kp around 0.5-1.0.
    
    candidates = []
    import itertools
    
    # Reduced search space for speed
    s_kps = [0.6, 1.0]
    s_kis = [0.01, 0.1]
    s_kds = [0.0, 0.5]
    
    # Reduced search space for distance
    d_kps = [0.3, 0.6]
    d_kis = [0.01, 0.05]
    d_kds = [0.1, 0.5]
    
    for skp, ski, skd, dkp, dki, dkd in itertools.product(s_kps, s_kis, s_kds, d_kps, d_kis, d_kds):
        s_gains = {'kp': skp, 'ki': ski, 'kd': skd}
        d_gains = {'kp': dkp, 'ki': dki, 'kd': dkd}
        
        valid, score, rt, os, se, de, md = evaluate(s_gains, d_gains)
        if valid:
            if score < best_score:
                best_score = score
                best_gains = (s_gains, d_gains)
                print(f"New Best: Score={score:.3f}, RT={rt}, OS={os:.2f}, SE={se:.3f}, DE={de:.3f}, MD={md:.2f}")
                print(f"  Speed: {s_gains}")
                print(f"  Dist: {d_gains}")
                
    if best_gains:
        s_gains, d_gains = best_gains
        results = {
            'pid_speed': s_gains,
            'pid_distance': d_gains
        }
        with open('tuning_results.yaml', 'w') as f:
            yaml.dump(results, f)
        print("Tuning complete. Saved to tuning_results.yaml")
    else:
        print("No valid gains found. Saving fallback.")
        # Fallback
        results = {
            'pid_speed': {'kp': 0.8, 'ki': 0.05, 'kd': 0.0},
            'pid_distance': {'kp': 0.5, 'ki': 0.02, 'kd': 0.5}
        }
        with open('tuning_results.yaml', 'w') as f:
            yaml.dump(results, f)

if __name__ == '__main__':
    tune()

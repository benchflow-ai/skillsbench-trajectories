import yaml
import csv
import math
from acc_system import AdaptiveCruiseControl

def load_base_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config

def load_sensor_data():
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def run_sim(config, sensor_data, mode_filter=None):
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    ego_speed = 0.0
    
    results = []
    
    for row in sensor_data:
        time = float(row['time'])
        lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
        distance = float(row['distance']) if row['distance'] else None
        
        # Optional: optimization to only run relevant parts
        if mode_filter == 'cruise' and lead_speed is not None:
            break
        if mode_filter == 'follow' and lead_speed is None and time < 10.0:
            # Skip initial cruise part for distance tuning? 
            # Better to run full sim to ensure valid state transition
            pass
            
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        
        ego_speed += accel_cmd * dt
        if ego_speed < 0: ego_speed = 0
        
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'mode': mode,
            'distance': distance,
            'distance_error': dist_error
        })
    return results

def tune_speed(base_config, sensor_data):
    # Target: Rise time < 10s, Overshoot < 5%, SSE < 0.5
    best_score = float('inf')
    best_params = (0.5, 0.01, 0.0)
    
    kps = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    kis = [0.0, 0.01, 0.05, 0.1, 0.2]
    kds = [0.0, 0.1, 0.5]
    
    set_speed = base_config['acc_settings']['set_speed']
    
    print("Tuning Speed PID...")
    for kp in kps:
        for ki in kis:
            for kd in kds:
                config = base_config.copy()
                config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
                config['pid_distance'] = {'kp': 0, 'ki': 0, 'kd': 0} # Dummy
                
                results = run_sim(config, sensor_data, mode_filter='cruise')
                
                # Metrics
                speeds = [r['ego_speed'] for r in results]
                times = [r['time'] for r in results]
                
                # Rise time (0 to 90%)
                rise_time = 0
                for t, v in zip(times, speeds):
                    if v >= 0.9 * set_speed:
                        rise_time = t
                        break
                if rise_time == 0 and speeds[-1] < 0.9 * set_speed:
                    rise_time = 999
                
                # Overshoot
                max_speed = max(speeds)
                overshoot = (max_speed - set_speed) / set_speed * 100
                
                # SSE (last 5 seconds of cruise, assume cruise ends ~30s)
                # Actually just check the end of the run provided by mode_filter
                final_speed = speeds[-1]
                sse = abs(final_speed - set_speed)
                
                # Constraints
                valid = True
                if rise_time > 10.0: valid = False
                if overshoot > 5.0: valid = False
                if sse > 0.5: valid = False
                
                # Score (minimize rise time and sse)
                score = rise_time + sse * 10
                if not valid: score += 1000
                
                if score < best_score:
                    best_score = score
                    best_params = (kp, ki, kd)
                    # print(f"New best speed: {best_params} Score: {score} RT: {rise_time} OS: {overshoot} SSE: {sse}")
                    
    return best_params

def tune_distance(base_config, sensor_data, speed_params):
    # Target: Dist SSE < 2m, Min Dist > 5m
    best_score = float('inf')
    best_params = (0.5, 0.01, 0.0)
    
    kps = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    kis = [0.0, 0.01, 0.05, 0.1]
    kds = [0.0, 0.1, 0.5, 1.0]
    
    kp_s, ki_s, kd_s = speed_params
    base_config['pid_speed'] = {'kp': kp_s, 'ki': ki_s, 'kd': kd_s}
    
    print("Tuning Distance PID...")
    for kp in kps:
        for ki in kis:
            for kd in kds:
                config = base_config.copy()
                config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}
                
                results = run_sim(config, sensor_data)
                
                # Filter for follow mode
                follow_data = [r for r in results if r['mode'] == 'follow' or r['mode'] == 'emergency']
                
                if not follow_data:
                    continue
                    
                # Min Distance
                dists = [r['distance'] for r in follow_data if r['distance'] is not None]
                min_dist = min(dists) if dists else 0
                
                # SSE (Mean Absolute Error of distance error)
                errors = [abs(r['distance_error']) for r in follow_data if r['distance_error'] is not None]
                avg_error = sum(errors) / len(errors) if errors else 0
                
                # Constraints
                valid = True
                if min_dist < 5.0: valid = False
                if avg_error > 2.0: valid = False
                
                # Score
                score = avg_error
                if not valid: score += 1000
                
                if score < best_score:
                    best_score = score
                    best_params = (kp, ki, kd)
                    # print(f"New best dist: {best_params} Score: {score} MinD: {min_dist} AvgErr: {avg_error}")
                    
    return best_params

def main():
    config = load_base_config()
    data = load_sensor_data()
    
    kp_s, ki_s, kd_s = tune_speed(config, data)
    print(f"Best Speed PID: {kp_s}, {ki_s}, {kd_s}")
    
    kp_d, ki_d, kd_d = tune_distance(config, data, (kp_s, ki_s, kd_s))
    print(f"Best Distance PID: {kp_d}, {ki_d}, {kd_d}")
    
    with open('tuning_results.yaml', 'w') as f:
        f.write("pid_speed:\n")
        f.write(f"  kp: {kp_s}\n  ki: {ki_s}\n  kd: {kd_s}\n")
        f.write("pid_distance:\n")
        f.write(f"  kp: {kp_d}\n  ki: {ki_d}\n  kd: {kd_d}\n")

if __name__ == '__main__':
    main()

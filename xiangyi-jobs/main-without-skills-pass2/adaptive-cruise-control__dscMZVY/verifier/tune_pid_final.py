import csv
import yaml
from acc_system import AdaptiveCruiseControl

def load_config(config_file='vehicle_params.yaml'):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def load_sensor_data(sensor_file='sensor_data.csv'):
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data

def run_simulation_with_gains(config, speed_gains, distance_gains):
    config['pid_speed'] = speed_gains
    config['pid_distance'] = distance_gains
    
    acc = AdaptiveCruiseControl(config)
    sensor_data = load_sensor_data()
    dt = config['simulation']['dt']
    
    results = []
    ego_speed = 0.0
    
    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']
        
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance
        }
        results.append(result)
        
        if i < len(sensor_data) - 1:
            ego_speed = ego_speed + accel_cmd * dt
            ego_speed = max(0, ego_speed)
    
    return results

def evaluate_results(results):
    score = 0.0
    penalties = 0.0
    
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    if cruise_results:
        cruise_speeds = [r['ego_speed'] for r in cruise_results]
        
        # Rise time (target <10s) - find 95% of 30 m/s
        target = 30 * 0.95
        rise_time = None
        for r in cruise_results:
            if r['ego_speed'] >= target:
                rise_time = r['time']
                break
        
        if rise_time is not None:
            if rise_time <= 10:
                score += 50 * (1 - rise_time/10)
            else:
                penalties += (rise_time - 10) * 10
        else:
            penalties += 100
        
        # Overshoot (target <5%) - heavily penalize
        max_speed = max(cruise_speeds)
        overshoot = max(0, (max_speed - 30) / 30 * 100)
        if overshoot <= 5:
            score += 30
        else:
            penalties += (overshoot - 5) * 10
        
        # Steady-state error (target <0.5 m/s) - most important
        if len(cruise_results) > 200:
            late_cruise = cruise_results[-200:]
            avg_speed = sum(r['ego_speed'] for r in late_cruise) / len(late_cruise)
            ss_error = abs(30 - avg_speed)
            if ss_error <= 0.5:
                score += 50
            else:
                penalties += (ss_error - 0.5) * 30
    
    return score - penalties

def tune_pid():
    config = load_config()
    
    # Focus on speed control - smaller, more refined ranges
    kp_range = [1.0, 1.5, 2.0, 2.5, 3.0]
    ki_range = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
    kd_range = [0.05, 0.1, 0.15]
    
    best_score = float('-inf')
    best_params = None
    
    print("Starting final PID tuning (speed-focused)...")
    total_combos = len(kp_range) * len(ki_range) * len(kd_range)
    print(f"Testing {total_combos} speed PID combinations (distance PID will use best speed values)")
    
    tested = 0
    for speed_kp in kp_range:
        for speed_ki in ki_range:
            for speed_kd in kd_range:
                tested += 1
                if tested % 50 == 0:
                    print(f"  Tested {tested}/{total_combos}...")
                
                speed_gains = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
                dist_gains = {'kp': 2.0, 'ki': 0.1, 'kd': 0.0}  # Use reasonable defaults
                
                try:
                    results = run_simulation_with_gains(config, speed_gains, dist_gains)
                    score = evaluate_results(results)
                    
                    if score > best_score:
                        best_score = score
                        best_params = {
                            'speed_gains': speed_gains,
                            'dist_gains': dist_gains,
                            'score': score
                        }
                        print(f"    New best score: {score:.2f}")
                except Exception as e:
                    pass
    
    tuning_results = {
        'pid_speed': best_params['speed_gains'],
        'pid_distance': best_params['dist_gains'],
        'tuning_score': best_params['score']
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)
    
    print(f"\nTuning complete!")
    print(f"Best score: {best_score:.2f}")
    print(f"Speed PID: kp={best_params['speed_gains']['kp']}, ki={best_params['speed_gains']['ki']}, kd={best_params['speed_gains']['kd']}")
    print(f"Distance PID: kp={best_params['dist_gains']['kp']}, ki={best_params['dist_gains']['ki']}, kd={best_params['dist_gains']['kd']}")

if __name__ == '__main__':
    tune_pid()

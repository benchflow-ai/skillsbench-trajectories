import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl
import csv

def load_sensor_data():
    """Load sensor data from CSV file."""
    sensor_data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            sensor_data.append(data)
    return sensor_data

def evaluate_pid(config, sensor_data):
    """Evaluate PID performance."""
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']
    
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    
    speeds = []
    times = []
    distance_errors_follow = []
    distances_follow = []
    
    for data in sensor_data:
        time = data['time']
        lead_speed = data['lead_speed']
        distance = data['distance']
        
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
        speeds.append(ego_speed)
        times.append(time)
        
        if mode == 'follow' and distance_error is not None:
            distance_errors_follow.append(distance_error)
            distances_follow.append(distance)
    
    # Rise time
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= 0.9 * set_speed:
            rise_time = times[i]
            break
    
    # Overshoot
    max_speed = max(speeds)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
    
    # Steady-state speed error (last 30s in cruise)
    cruise_ss_error = abs(speeds[-1] - set_speed) if len(speeds) > 0 else 0
    
    # Distance steady-state error (last 50 samples in follow mode)
    distance_ss_error = np.mean(np.abs(distance_errors_follow[-50:])) if len(distance_errors_follow) > 50 else 0
    
    # Minimum distance
    min_distance = min(distances_follow) if distances_follow else float('inf')
    
    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'cruise_ss_error': cruise_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance
    }

def tune_pid():
    """Tune PID parameters with refined ranges."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    sensor_data = load_sensor_data()
    
    print("Refined PID tuning...")
    
    best_score = float('inf')
    best_params = None
    
    # Refined candidates - lower Ki, higher Kd for speed to reduce overshoot
    speed_candidates = [
        {'kp': 1.0, 'ki': 0.01, 'kd': 1.5},
        {'kp': 1.2, 'ki': 0.02, 'kd': 2.0},
        {'kp': 0.8, 'ki': 0.01, 'kd': 1.2},
        {'kp': 1.5, 'ki': 0.02, 'kd': 2.5},
        {'kp': 1.0, 'ki': 0.015, 'kd': 1.8},
    ]
    
    # Higher Kp for distance to reduce steady-state error
    distance_candidates = [
        {'kp': 1.5, 'ki': 0.02, 'kd': 1.5},
        {'kp': 2.0, 'ki': 0.03, 'kd': 2.0},
        {'kp': 1.8, 'ki': 0.025, 'kd': 1.8},
        {'kp': 2.5, 'ki': 0.04, 'kd': 2.5},
        {'kp': 1.2, 'ki': 0.015, 'kd': 1.2},
    ]
    
    for speed_pid in speed_candidates:
        for distance_pid in distance_candidates:
            config['pid_speed'] = speed_pid
            config['pid_distance'] = distance_pid
            
            metrics = evaluate_pid(config, sensor_data)
            
            # Weighted scoring
            score = 0
            if metrics['rise_time'] is None or metrics['rise_time'] > 10:
                score += 1000  # Penalty for slow rise
            score += max(0, metrics['overshoot_pct'] - 5) * 50  # Heavy penalty for overshoot > 5%
            score += max(0, metrics['cruise_ss_error'] - 0.5) * 100  # Penalty for speed error > 0.5
            score += max(0, metrics['distance_ss_error'] - 2) * 50  # Penalty for distance error > 2m
            if metrics['min_distance'] < 5:
                score += (5 - metrics['min_distance']) * 200  # Heavy penalty for unsafe distance
            
            if score < best_score:
                best_score = score
                best_params = {
                    'pid_speed': speed_pid.copy(),
                    'pid_distance': distance_pid.copy(),
                    'metrics': metrics
                }
                print(f"New best - Speed: {speed_pid}, Distance: {distance_pid}")
                print(f"  Metrics: {metrics}")
                print(f"  Score: {score:.2f}\n")
    
    print(f"\n=== FINAL BEST PARAMETERS ===")
    print(f"Speed PID: {best_params['pid_speed']}")
    print(f"Distance PID: {best_params['pid_distance']}")
    print(f"Metrics: {best_params['metrics']}")
    print(f"Score: {best_score:.2f}")
    
    output = {
        'pid_speed': best_params['pid_speed'],
        'pid_distance': best_params['pid_distance']
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(output, f, default_flow_style=False)
    
    print("\nSaved to tuning_results.yaml")

if __name__ == '__main__':
    tune_pid()

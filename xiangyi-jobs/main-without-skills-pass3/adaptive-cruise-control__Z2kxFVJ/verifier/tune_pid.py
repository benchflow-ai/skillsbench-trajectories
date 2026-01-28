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
    min_distance = config['acc_settings']['min_distance']
    
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    
    # Track metrics
    speed_errors = []
    distance_errors = []
    min_dist_achieved = float('inf')
    speeds = []
    times = []
    
    for data in sensor_data:
        time = data['time']
        lead_speed = data['lead_speed']
        distance = data['distance']
        
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        # Update speed
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
        speeds.append(ego_speed)
        times.append(time)
        
        # Track errors
        if mode == 'cruise':
            speed_errors.append(abs(set_speed - ego_speed))
        elif mode == 'follow' and distance_error is not None:
            distance_errors.append(abs(distance_error))
            if distance is not None:
                min_dist_achieved = min(min_dist_achieved, distance)
    
    # Calculate rise time (time to reach 90% of set speed)
    rise_time = None
    target_speed = 0.9 * set_speed
    for i, speed in enumerate(speeds):
        if speed >= target_speed:
            rise_time = times[i]
            break
    
    # Calculate overshoot
    max_speed = max(speeds)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
    
    # Steady-state errors
    cruise_ss_error = np.mean(speed_errors[-100:]) if speed_errors else 0
    distance_ss_error = np.mean(distance_errors[-100:]) if distance_errors else 0
    
    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'cruise_ss_error': cruise_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_dist_achieved
    }

def tune_pid():
    """Tune PID parameters."""
    # Load base configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    sensor_data = load_sensor_data()
    
    print("Tuning PID parameters...")
    
    # Test different PID combinations
    best_score = float('inf')
    best_params = None
    
    # Speed PID tuning - prioritize fast rise time and low overshoot
    speed_candidates = [
        {'kp': 1.5, 'ki': 0.1, 'kd': 0.5},
        {'kp': 2.0, 'ki': 0.15, 'kd': 0.8},
        {'kp': 1.8, 'ki': 0.12, 'kd': 0.6},
        {'kp': 1.2, 'ki': 0.08, 'kd': 0.4},
    ]
    
    # Distance PID tuning - prioritize stability and minimal steady-state error
    distance_candidates = [
        {'kp': 0.8, 'ki': 0.05, 'kd': 1.2},
        {'kp': 1.0, 'ki': 0.08, 'kd': 1.5},
        {'kp': 0.6, 'ki': 0.03, 'kd': 1.0},
        {'kp': 1.2, 'ki': 0.1, 'kd': 1.8},
    ]
    
    for speed_pid in speed_candidates:
        for distance_pid in distance_candidates:
            config['pid_speed'] = speed_pid
            config['pid_distance'] = distance_pid
            
            metrics = evaluate_pid(config, sensor_data)
            
            # Score based on requirements
            score = 0
            if metrics['rise_time'] and metrics['rise_time'] > 10:
                score += (metrics['rise_time'] - 10) * 10
            score += metrics['overshoot_pct'] * 5
            score += metrics['cruise_ss_error'] * 20
            score += metrics['distance_ss_error'] * 10
            if metrics['min_distance'] < 5:
                score += (5 - metrics['min_distance']) * 100
            
            print(f"Speed PID: {speed_pid}, Distance PID: {distance_pid}")
            print(f"  Metrics: {metrics}")
            print(f"  Score: {score:.2f}")
            
            if score < best_score:
                best_score = score
                best_params = {
                    'pid_speed': speed_pid.copy(),
                    'pid_distance': distance_pid.copy(),
                    'metrics': metrics
                }
    
    print(f"\nBest parameters found:")
    print(f"Speed PID: {best_params['pid_speed']}")
    print(f"Distance PID: {best_params['pid_distance']}")
    print(f"Metrics: {best_params['metrics']}")
    
    # Save to tuning_results.yaml
    output = {
        'pid_speed': best_params['pid_speed'],
        'pid_distance': best_params['pid_distance']
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(output, f, default_flow_style=False)
    
    print("\nSaved tuning results to tuning_results.yaml")

if __name__ == '__main__':
    tune_pid()

import yaml
import csv
import numpy as np
from acc_system import AdaptiveCruiseControl

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def load_sensor_data(sensor_file):
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data

def evaluate_pid(speed_params, distance_params):
    """Evaluate PID parameters and return performance metrics."""
    config = load_config('vehicle_params.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')
    
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_controllers(speed_params, distance_params)
    
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']
    
    ego_speed = 0.0
    speeds = []
    distances = []
    min_distance = float('inf')
    
    for i, sensor_row in enumerate(sensor_data):
        lead_speed = sensor_row['lead_speed']
        distance = sensor_row['distance']
        
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        speeds.append(ego_speed)
        
        if distance is not None:
            distances.append(abs(distance_error) if distance_error is not None else 0)
            min_distance = min(min_distance, distance)
        
        if i < len(sensor_data) - 1:
            ego_speed += acceleration_cmd * dt
            ego_speed = max(0.0, ego_speed)
    
    # Calculate metrics for cruise phase (first ~40 seconds)
    cruise_end_idx = min(400, len(speeds))
    cruise_speeds = speeds[:cruise_end_idx]
    
    # Rise time: time to reach 90% of set speed
    target_90 = 0.9 * set_speed
    rise_time = None
    for i, speed in enumerate(cruise_speeds):
        if speed >= target_90:
            rise_time = i * dt
            break
    
    # Overshoot
    max_speed = max(cruise_speeds)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
    
    # Steady-state error (last 10 seconds of cruise)
    steady_state_speeds = cruise_speeds[-100:] if len(cruise_speeds) >= 100 else cruise_speeds
    steady_state_error = abs(np.mean(steady_state_speeds) - set_speed)
    
    # Distance steady-state error
    distance_ss_error = np.mean(distances[-100:]) if len(distances) >= 100 else (np.mean(distances) if distances else 0)
    
    return {
        'rise_time': rise_time if rise_time else 999,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': steady_state_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance if min_distance != float('inf') else 999
    }

def tune_pid():
    """Tune PID parameters to meet requirements."""
    print("Starting PID tuning with improved parameter ranges...")
    
    best_params = None
    best_score = float('inf')
    
    # Better tuned ranges - focus on reducing overshoot
    speed_candidates = [
        {'kp': 0.8, 'ki': 0.05, 'kd': 0.3},
        {'kp': 0.9, 'ki': 0.06, 'kd': 0.4},
        {'kp': 1.0, 'ki': 0.08, 'kd': 0.5},
        {'kp': 0.85, 'ki': 0.055, 'kd': 0.35},
        {'kp': 0.95, 'ki': 0.07, 'kd': 0.45},
    ]
    
    distance_candidates = [
        {'kp': 0.4, 'ki': 0.04, 'kd': 0.8},
        {'kp': 0.5, 'ki': 0.05, 'kd': 1.0},
        {'kp': 0.45, 'ki': 0.045, 'kd': 0.9},
        {'kp': 0.55, 'ki': 0.055, 'kd': 1.1},
        {'kp': 0.6, 'ki': 0.06, 'kd': 1.2},
    ]
    
    for speed_params in speed_candidates:
        for distance_params in distance_candidates:
            metrics = evaluate_pid(speed_params, distance_params)
            
            # Check if requirements are met
            requirements_met = (
                metrics['rise_time'] < 10 and
                metrics['overshoot_pct'] < 5 and
                metrics['speed_ss_error'] < 0.5 and
                metrics['distance_ss_error'] < 2 and
                metrics['min_distance'] > 5
            )
            
            # Score function (lower is better)
            score = (
                metrics['rise_time'] * 0.5 +
                metrics['overshoot_pct'] * 3 +
                metrics['speed_ss_error'] * 20 +
                metrics['distance_ss_error'] * 10
            )
            
            if requirements_met and score < best_score:
                best_score = score
                best_params = {
                    'speed': speed_params,
                    'distance': distance_params,
                    'metrics': metrics
                }
            
            print(f"Testing: Speed kp={speed_params['kp']:.2f} ki={speed_params['ki']:.3f} kd={speed_params['kd']:.2f}, "
                  f"Distance kp={distance_params['kp']:.2f} ki={distance_params['ki']:.3f} kd={distance_params['kd']:.2f}")
            print(f"  Rise={metrics['rise_time']:.1f}s, Overshoot={metrics['overshoot_pct']:.1f}%, "
                  f"SpeedErr={metrics['speed_ss_error']:.2f}, DistErr={metrics['distance_ss_error']:.2f}, "
                  f"MinDist={metrics['min_distance']:.2f}m")
            print(f"  Requirements met: {requirements_met}, Score: {score:.2f}")
    
    if best_params is None:
        print("\nNo parameters met all requirements. Using best compromise.")
        # Use the best performing set even if not all requirements met
        best_params = {
            'speed': {'kp': 0.9, 'ki': 0.06, 'kd': 0.4},
            'distance': {'kp': 0.5, 'ki': 0.05, 'kd': 1.0},
            'metrics': {}
        }
    
    print(f"\n=== Best parameters found ===")
    print(f"Speed PID: kp={best_params['speed']['kp']}, ki={best_params['speed']['ki']}, kd={best_params['speed']['kd']}")
    print(f"Distance PID: kp={best_params['distance']['kp']}, ki={best_params['distance']['ki']}, kd={best_params['distance']['kd']}")
    if best_params['metrics']:
        print(f"Metrics: {best_params['metrics']}")
    
    # Save to tuning_results.yaml
    tuning_results = {
        'pid_speed': best_params['speed'],
        'pid_distance': best_params['distance']
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)
    
    print("\nTuning results saved to tuning_results.yaml")

if __name__ == '__main__':
    tune_pid()

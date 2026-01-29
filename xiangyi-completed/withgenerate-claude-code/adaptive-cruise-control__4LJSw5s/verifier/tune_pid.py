"""
PID Parameter Tuning for ACC System

Uses grid search over parameter ranges to find gains that meet performance targets.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def evaluate_gains(speed_gains, distance_gains, config, sensor_data):
    """
    Evaluate PID gains against sensor data.
    
    Args:
        speed_gains: Dict with 'kp', 'ki', 'kd' for speed control
        distance_gains: Dict with 'kp', 'ki', 'kd' for distance control
        config: Vehicle configuration
        sensor_data: Sensor data dataframe
        
    Returns:
        Dict with performance metrics
    """
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_gains(speed_gains, distance_gains)
    
    dt = config['control']['control_period']
    ego_speed = 0.0
    
    results = {
        'time': [],
        'ego_speed': [],
        'mode': [],
        'distance_error': [],
        'acceleration_cmd': []
    }
    
    # Simulate
    for idx in range(len(sensor_data)):
        row = sensor_data.iloc[idx]
        time = row['time']
        lead_speed = row['lead_speed']
        distance = row['distance']
        
        if pd.isna(lead_speed):
            lead_speed = None
        if pd.isna(distance):
            distance = None
        
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
        results['time'].append(time)
        results['ego_speed'].append(ego_speed)
        results['mode'].append(mode)
        results['distance_error'].append(distance_error if distance_error is not None else np.nan)
        results['acceleration_cmd'].append(accel_cmd)
    
    results_df = pd.DataFrame(results)
    
    # Calculate metrics
    set_speed = config['acc_settings']['set_speed']
    
    # Speed metrics (cruise phase)
    cruise_data = results_df[results_df['mode'] == 'cruise']
    
    if len(cruise_data) > 0:
        # Rise time: time to reach 95% of set speed
        target_speed = 0.95 * set_speed
        cruise_above = cruise_data[cruise_data['ego_speed'] >= target_speed]
        
        if len(cruise_above) > 0:
            rise_time = cruise_above['time'].iloc[0]
        else:
            rise_time = float('inf')
        
        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot = max(0, max_speed - set_speed)
        overshoot_pct = (overshoot / set_speed) * 100
        
        # Steady-state error (last 10% of cruise)
        ss_data = cruise_data.iloc[max(0, int(len(cruise_data)*0.9)):]
        ss_error = abs(ss_data['ego_speed'].mean() - set_speed)
    else:
        rise_time = float('inf')
        overshoot_pct = 100.0
        ss_error = 100.0
    
    # Distance metrics
    follow_data = results_df[results_df['mode'] == 'follow']
    if len(follow_data) > 0:
        ss_follow = follow_data.iloc[max(0, int(len(follow_data)*0.9)):]
        distance_ss_error = abs(ss_follow['distance_error'].mean())
    else:
        distance_ss_error = 100.0
    
    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': ss_error,
        'distance_ss_error': distance_ss_error,
        'score': rise_time + overshoot_pct + ss_error + distance_ss_error * 2
    }


def tune_pid(config_file, sensor_data_file):
    """
    Tune PID parameters using grid search.
    
    Args:
        config_file: Path to vehicle_params.yaml
        sensor_data_file: Path to sensor_data.csv
    """
    # Load configuration and data
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    sensor_data = pd.read_csv(sensor_data_file)
    
    print("Tuning PID parameters (this may take a minute)...")
    
    # Grid search parameters
    kp_values = np.linspace(0.5, 3.0, 6)  # Speed Kp: 0.5-3.0
    ki_values = np.linspace(0.01, 0.3, 4)  # Speed Ki: 0.01-0.3
    kd_values = np.linspace(0.5, 2.0, 4)   # Speed Kd: 0.5-2.0
    
    dist_kp = np.linspace(0.1, 1.0, 5)     # Distance Kp: 0.1-1.0
    dist_ki = np.linspace(0.01, 0.15, 3)   # Distance Ki: 0.01-0.15
    dist_kd = np.linspace(0.1, 1.0, 5)     # Distance Kd: 0.1-1.0
    
    best_score = float('inf')
    best_gains = None
    evaluations = 0
    
    # Coarse search first
    print("  Coarse search...")
    for kp in kp_values[::2]:
        for ki in ki_values[::2]:
            for kd in kd_values[::2]:
                for d_kp in dist_kp[::2]:
                    for d_ki in dist_ki[::2]:
                        for d_kd in dist_kd[::2]:
                            evaluations += 1
                            # Convert numpy to float to avoid YAML serialization issues
                            speed_gains = {'kp': float(kp), 'ki': float(ki), 'kd': float(kd)}
                            dist_gains = {'kp': float(d_kp), 'ki': float(d_ki), 'kd': float(d_kd)}
                            
                            metrics = evaluate_gains(speed_gains, dist_gains, config, sensor_data)
                            
                            if metrics['score'] < best_score:
                                best_score = metrics['score']
                                best_gains = (speed_gains, dist_gains)
                                print(f"    New best score: {best_score:.2f}")
    
    # Fine search around best
    if best_gains:
        print("  Fine search...")
        speed_gains, dist_gains = best_gains
        
        # Refine speed gains
        for kp in np.linspace(max(0.1, speed_gains['kp']-0.3), speed_gains['kp']+0.3, 3):
            for ki in np.linspace(max(0.001, speed_gains['ki']-0.05), speed_gains['ki']+0.05, 3):
                for kd in np.linspace(max(0.1, speed_gains['kd']-0.3), speed_gains['kd']+0.3, 3):
                    evaluations += 1
                    new_speed_gains = {'kp': float(kp), 'ki': float(ki), 'kd': float(kd)}
                    
                    metrics = evaluate_gains(new_speed_gains, dist_gains, config, sensor_data)
                    
                    if metrics['score'] < best_score:
                        best_score = metrics['score']
                        speed_gains = new_speed_gains
                        best_gains = (speed_gains, dist_gains)
                        print(f"    New best score: {best_score:.2f}")
    
    print(f"\nTuning complete ({evaluations} evaluations)")
    
    speed_gains, dist_gains = best_gains
    
    # Verify best gains
    print("\nBest gains found:")
    print(f"Speed PID: Kp={speed_gains['kp']:.4f}, Ki={speed_gains['ki']:.4f}, Kd={speed_gains['kd']:.4f}")
    print(f"Distance PID: Kp={dist_gains['kp']:.4f}, Ki={dist_gains['ki']:.4f}, Kd={dist_gains['kd']:.4f}")
    
    metrics = evaluate_gains(speed_gains, dist_gains, config, sensor_data)
    print(f"\nPerformance metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {metrics['speed_ss_error']:.3f} m/s (target: <0.5)")
    print(f"  Distance SS error: {metrics['distance_ss_error']:.2f}m (target: <2m)")
    
    # Save results
    tuning_results = {
        'pid_speed': speed_gains,
        'pid_distance': dist_gains
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)
    
    print("\n✓ Tuning results saved to tuning_results.yaml")
    return tuning_results


if __name__ == '__main__':
    tune_pid('vehicle_params.yaml', 'sensor_data.csv')

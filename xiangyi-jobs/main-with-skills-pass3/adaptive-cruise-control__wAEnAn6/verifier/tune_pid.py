
import pandas as pd
import yaml
import os
from acc_system import AdaptiveCruiseControl
import numpy as np

def calculate_metrics(df, config):
    # Speed metrics (during cruise, t < 30)
    cruise_df = df[df['time'] < 30.0]
    target_speed = config['acc_settings']['set_speed']
    
    # Rise time (10% to 90%)
    v10 = 0.1 * target_speed
    v90 = 0.9 * target_speed
    t10 = cruise_df[cruise_df['ego_speed'] >= v10]['time'].min()
    t90 = cruise_df[cruise_df['ego_speed'] >= v90]['time'].min()
    rise_time = t90 - t10 if t10 is not None and t90 is not None else float('inf')
    
    # Overshoot
    max_v = cruise_df['ego_speed'].max()
    overshoot = (max_v - target_speed) / target_speed * 100 if max_v > target_speed else 0.0
    
    # SS Error (last 5s of cruise)
    ss_cruise = cruise_df[cruise_df['time'] >= 25.0]
    ss_error_speed = abs(ss_cruise['ego_speed'].mean() - target_speed)
    
    # Distance metrics (during follow, t >= 30)
    follow_df = df[df['time'] >= 30.0]
    follow_df_valid = follow_df[follow_df['distance_error'].notna()]
    
    if len(follow_df_valid) > 0:
        ss_error_dist = abs(follow_df_valid['distance_error'].iloc[-50:].mean())
        min_dist = follow_df_valid['distance'].min()
    else:
        ss_error_dist = float('inf')
        min_dist = 0.0
        
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_error_speed': ss_error_speed,
        'ss_error_dist': ss_error_dist,
        'min_dist': min_dist
    }

def run_sim_with_params(speed_gains, dist_gains, config, sensor_df):
    config['pid_speed'].update(speed_gains)
    config['pid_distance'].update(dist_gains)
    
    acc = AdaptiveCruiseControl(config)
    results = []
    ego_speed = sensor_df.iloc[0]['ego_speed']
    ego_pos = 0.0
    recorded_ego_pos = 0.0
    dt = config['simulation']['dt']
    
    for i, row in sensor_df.iterrows():
        t = row['time']
        lead_speed = row['lead_speed']
        rec_distance = row['distance']
        rec_ego_speed = row['ego_speed']
        
        sim_distance = None
        if not pd.isna(rec_distance):
            lead_pos = recorded_ego_pos + rec_distance
            sim_distance = lead_pos - ego_pos
            
        if abs(t - 30.0) < 0.05:
            d_str = f"{sim_distance:.2f}" if sim_distance is not None else "None"
            print(f"DEBUG: At t={t:.1f}, recorded_ego_pos={recorded_ego_pos:.2f}, ego_pos={ego_pos:.2f}, sim_distance={d_str}")
        
        ls_input = lead_speed if not pd.isna(lead_speed) else None
        dist_input = sim_distance if sim_distance is not None else None
        
        accel_cmd, mode, dist_err = acc.compute(ego_speed, ls_input, dist_input, dt)
        
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'distance_error': dist_err,
            'distance': sim_distance
        })
        
        ego_pos += ego_speed * dt
        recorded_ego_pos += rec_ego_speed * dt
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
    return pd.DataFrame(results)

def tune():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    sensor_df = pd.read_csv('sensor_data.csv')
    
    best_speed_gains = {'kp': 1.0, 'ki': 0.1, 'kd': 0.0}
    best_dist_gains = {'kp': 1.0, 'ki': 0.1, 'kd': 0.0}
    
    # Search for speed gains
    best_score = float('inf')
    for kp in np.linspace(0.05, 0.5, 20):
        for ki in np.linspace(0.0, 0.05, 10):
            gains = {'kp': float(kp), 'ki': float(ki), 'kd': 0.1}
            df = run_sim_with_params(gains, {'kp': 1.0, 'ki': 0.1, 'kd': 0.5}, config, sensor_df)
            m = calculate_metrics(df, config)
            if 9.0 < m['rise_time'] < 10.0 and m['min_dist'] > 5.0:
                score = abs(m['ss_error_speed']) + m['overshoot']
                if score < best_score:
                    best_score = score
                    best_speed_gains = gains
    
    print(f"Best speed gains: {best_speed_gains}")
    
    # Search for distance gains
    best_score = float('inf')
    for kp in [0.1, 0.2, 0.3, 0.4, 0.5]:
        for ki in [0.0, 0.001, 0.005, 0.01]:
            for kd in [0.1, 0.5, 1.0]:
                gains = {'kp': float(kp), 'ki': float(ki), 'kd': float(kd)}
                df = run_sim_with_params(best_speed_gains, gains, config, sensor_df)
                m = calculate_metrics(df, config)
                if m['min_dist'] > 5.0:
                    score = m['ss_error_dist']
                    if score < best_score:
                        best_score = score
                        best_dist_gains = gains
                        
    print(f"Best distance gains: {best_dist_gains}")
    
    tuning_results = {
        'pid_speed': best_speed_gains,
        'pid_distance': best_dist_gains
    }
    
    # Final check
    df = run_sim_with_params(best_speed_gains, best_dist_gains, config, sensor_df)
    m = calculate_metrics(df, config)
    print(f"Final Metrics: {m}")
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

if __name__ == "__main__":
    tune()

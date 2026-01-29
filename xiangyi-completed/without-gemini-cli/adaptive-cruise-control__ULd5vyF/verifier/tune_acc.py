import pandas as pd
import yaml
import numpy as np
from simulation import run_simulation

def evaluate(df):
    # Speed metrics (First Cruise mode phase)
    # Find the end of the first cruise phase
    mode_diff = df['mode'] != df['mode'].shift(1)
    mode_changes = df[mode_diff].index.tolist()
    
    first_cruise_end_idx = mode_changes[1] if len(mode_changes) > 1 else len(df)
    first_cruise_data = df.iloc[:first_cruise_end_idx]
    first_cruise_data = first_cruise_data[first_cruise_data['mode'] == 'cruise']
    
    target_speed = 30.0
    
    # Rise time: time to reach 90% of target speed (27.0 m/s)
    reached_90 = first_cruise_data[first_cruise_data['ego_speed'] >= 0.9 * target_speed]
    rise_time = reached_90['time'].iloc[0] if not reached_90.empty else 150.0
    
    # Overshoot
    max_speed = first_cruise_data['ego_speed'].max()
    overshoot = (max_speed - target_speed) / target_speed * 100
    overshoot = max(0, overshoot)
    
    # SSE speed
    steady_speed_data = first_cruise_data[first_cruise_data['time'] > rise_time + 5]
    sse_speed = abs(steady_speed_data['ego_speed'] - target_speed).mean() if not steady_speed_data.empty else 100.0
    
    # Distance metrics (Follow mode)
    follow_data = df[df['mode'] == 'follow']
    if not follow_data.empty:
        # Evaluate SSE dist during the last part of follow mode to ensure it's "steady"
        follow_start_time = follow_data['time'].iloc[0]
        follow_end_time = follow_data['time'].iloc[-1]
        steady_follow_data = follow_data[follow_data['time'] > follow_start_time + 10]
        if not steady_follow_data.empty:
            sse_dist = abs(steady_follow_data['distance_error']).mean()
        else:
            sse_dist = abs(follow_data['distance_error']).mean()
        min_dist = follow_data['distance'].min()
    else:
        sse_dist = 100.0
        min_dist = 0.0
        
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'sse_speed': sse_speed,
        'sse_dist': sse_dist,
        'min_dist': min_dist
    }

def tune():
    best_results = None
    best_gains = None
    
    # Heuristic tuning
    kp_speed = 8.0
    ki_speed = 0.01
    kd_speed = 2.0
    
    kp_speed = 8.0
    ki_speed = 0.01
    kd_speed = 2.0
    
    kp_dist = 9.9
    ki_dist = 2.0
    kd_dist = 4.0

    gains = {
        'pid_speed': {'kp': kp_speed, 'ki': ki_speed, 'kd': kd_speed},
        'pid_distance': {'kp': kp_dist, 'ki': ki_dist, 'kd': kd_dist}
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(gains, f)
        
    df = run_simulation()
    metrics = evaluate(df)
    print(f"Metrics: {metrics}")
    
    # If metrics are not met, try to adjust
    # For now, let's try a few combinations if needed.
    # But let's check these first.

if __name__ == "__main__":
    tune()

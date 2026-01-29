import pandas as pd
import yaml
import numpy as np
import os
from simulation import run_simulation

def evaluate_performance(df):
    df_cruise = df[df['mode'] == 'cruise'].copy()
    speed_metrics = {}
    if not df_cruise.empty:
        target_speed = 30.0
        reach_90 = df_cruise[df_cruise['ego_speed'] >= 0.9 * target_speed]
        if not reach_90.empty:
            speed_metrics['rise_time'] = reach_90.iloc[0]['time']
        else:
            speed_metrics['rise_time'] = float('inf')
        speed_metrics['max_speed'] = df_cruise['ego_speed'].max()
        speed_metrics['overshoot_pct'] = max(0, (speed_metrics['max_speed'] - target_speed) / target_speed * 100)
        speed_metrics['ss_error'] = abs(df_cruise.iloc[-1]['ego_speed'] - target_speed)

    df_follow = df[df['mode'] == 'follow'].copy()
    dist_metrics = {}
    if not df_follow.empty:
        dist_metrics['min_dist'] = df_follow['distance'].min()
        # Steady state error: last 10 seconds of follow mode
        last_10s = df_follow[df_follow['time'] > df_follow['time'].max() - 10]
        dist_metrics['ss_error'] = last_10s['distance_error'].abs().mean()
    
    return speed_metrics, dist_metrics

def main():
    candidates = [
        {'speed': {'kp': 0.5, 'ki': 0.0, 'kd': 1.0}, 'dist': {'kp': 5.0, 'ki': 0.0, 'kd': 2.0}},
        {'speed': {'kp': 0.4, 'ki': 0.0, 'kd': 1.5}, 'dist': {'kp': 8.0, 'ki': 0.0, 'kd': 4.0}},
        {'speed': {'kp': 0.6, 'ki': 0.0, 'kd': 0.5}, 'dist': {'kp': 3.0, 'ki': 0.0, 'kd': 1.0}},
    ]
    
    for i, cand in enumerate(candidates):
        tuning = {'pid_speed': cand['speed'], 'pid_distance': cand['dist']}
        with open('tuning_results.yaml', 'w') as f:
            yaml.dump(tuning, f)
        
        df = run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv')
        speed_perf, dist_perf = evaluate_performance(df)
        print(f"Candidate {i}:")
        print(f"  Speed: {speed_perf}")
        print(f"  Dist:  {dist_perf}")

if __name__ == "__main__":
    main()
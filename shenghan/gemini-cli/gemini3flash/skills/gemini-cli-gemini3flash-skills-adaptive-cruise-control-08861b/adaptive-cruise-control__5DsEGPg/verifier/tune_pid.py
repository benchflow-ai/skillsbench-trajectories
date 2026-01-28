
import pandas as pd
import yaml
import numpy as np
from simulation import run_simulation

def evaluate(df):
    # Speed metrics (Cruise mode)
    df_cruise = df[df['mode'] == 'cruise']
    
    # Rise time: time to reach 90% of 30m/s (27m/s)
    reached_27 = df_cruise[df_cruise['ego_speed'] >= 27]
    if not reached_27.empty:
        # Assuming starts at t=0
        rise_time = reached_27['time'].iloc[0]
    else:
        rise_time = 150.0
    
    # Overshoot
    max_speed = df['ego_speed'].max()
    overshoot = (max_speed - 30.0) / 30.0 * 100
    overshoot = max(0, overshoot)
    
    # Speed Steady-state error
    df_ss_speed = df[(df['mode'] == 'cruise') & (df['time'] >= 20)]
    ss_error_speed = np.abs(30.0 - df_ss_speed['ego_speed']).mean() if not df_ss_speed.empty else 0.0
    
    # Distance Steady-state error
    df_follow = df[df['mode'] == 'follow']
    df_ss_dist = df_follow[(df_follow['time'] >= 100) & (df_follow['time'] <= 150)]
    ss_error_dist = np.abs(df_ss_dist['distance_error']).mean() if not df_ss_dist.empty else 0.0
    
    # Minimum distance
    min_dist = df['distance'].dropna().min() if not df['distance'].dropna().empty else 150.0
    
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_error_speed': ss_error_speed,
        'ss_error_dist': ss_error_dist,
        'min_dist': min_dist
    }

if __name__ == "__main__":
    df = run_simulation()
    metrics = evaluate(df)
    print("Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

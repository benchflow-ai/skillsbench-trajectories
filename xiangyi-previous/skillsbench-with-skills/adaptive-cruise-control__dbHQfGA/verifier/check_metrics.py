import pandas as pd
import numpy as np

def check():
    df = pd.read_csv('simulation_results.csv')
    
    # Speed metrics (during cruise mode)
    cruise_df = df[df['mode'] == 'cruise']
    if not cruise_df.empty:
        target_speed = 30.0
        reached_90 = cruise_df[cruise_df['ego_speed'] >= 0.9 * target_speed]
        if not reached_90.empty:
            rise_time = reached_90.iloc[0]['time']
            print(f"Speed Rise Time: {rise_time}s")
        
        max_speed = cruise_df['ego_speed'].max()
        overshoot = (max_speed - target_speed) / target_speed * 100
        print(f"Speed Overshoot: {max(0, overshoot):.2f}%")

        last_cruise = cruise_df[cruise_df['time'] > cruise_df['time'].max() - 2]
        ss_error_speed = np.abs(last_cruise['ego_speed'] - target_speed).mean()
        print(f"Speed SS Error: {ss_error_speed:.2f} m/s")

    # Distance metrics (during follow mode)
    # Only consider follow mode where we are actually following (ego_speed < set_speed - 0.5)
    follow_df = df[(df['mode'] == 'follow') & (df['ego_speed'] < 29.5)]
    if not follow_df.empty:
        dist_errs = pd.to_numeric(follow_df['distance_error'], errors='coerce').dropna()
        ss_error_dist = np.abs(dist_errs).mean()
        print(f"Distance SS Error (Filtered): {ss_error_dist:.2f} m")
    else:
        print("No stable follow mode detected (ego_speed < 29.5)")

    min_dist = pd.to_numeric(df['distance'], errors='coerce').min()
    print(f"Minimum Distance: {min_dist:.2f} m")

check()

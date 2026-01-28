import pandas as pd
import numpy as np

def evaluate():
    df = pd.read_csv('simulation_results.csv')
    
    # Speed metrics (cruise mode)
    cruise_df = df[df['mode'] == 'cruise']
    if not cruise_df.empty:
        target_speed = 30.0
        # Rise time (0 to 90% of target speed)
        reached_90 = cruise_df[cruise_df['ego_speed'] >= 0.9 * target_speed]
        if not reached_90.empty:
            rise_time = reached_90.iloc[0]['time']
            print(f"Rise time: {rise_time}s")
        else:
            print("Rise time: Target speed not reached")
            
        overshoot = (cruise_df['ego_speed'].max() - target_speed) / target_speed * 100
        print(f"Overshoot: {max(0, overshoot):.2f}%")
        
        # Steady state error (last 10s of cruise if any)
        last_cruise = cruise_df.tail(100)
        ss_error_speed = abs(last_cruise['ego_speed'].mean() - target_speed)
        print(f"Speed SS Error: {ss_error_speed:.2f} m/s")

    # Distance metrics (follow mode)
    follow_df = df[df['mode'] == 'follow']
    if not follow_df.empty:
        ss_error_dist = abs(follow_df['distance_error'].tail(100).mean())
        print(f"Distance SS Error: {ss_error_dist:.2f} m")
        
        min_dist = df['distance'].dropna().min()
        print(f"Minimum distance: {min_dist:.2f} m")

    # Check constraints
    max_accel = df['acceleration_cmd'].max()
    min_accel = df['acceleration_cmd'].min()
    print(f"Accel range: [{min_accel}, {max_accel}]")

if __name__ == "__main__":
    evaluate()

import pandas as pd
import numpy as np

def check():
    df = pd.read_csv('simulation_results.csv')
    
    # Speed Check
    cruise_df = df[df['time'] < 30]
    target = 30.0
    speeds = cruise_df['ego_speed'].values
    times = cruise_df['time'].values
    
    t_10 = next((t for t, s in zip(times, speeds) if s >= 0.1 * target), None)
    t_90 = next((t for t, s in zip(times, speeds) if s >= 0.9 * target), None)
    rise_time = t_90 - t_10 if (t_10 and t_90) else None
    
    max_speed = np.max(df['ego_speed'].values)
    overshoot_perc = (max_speed - target) / target * 100 if max_speed > target else 0
    
    final_speed = df[df['time'] < 40]['ego_speed'].iloc[-1]
    ss_error_speed = abs(target - final_speed)
    
    print(f"Speed Rise Time: {rise_time} s")
    print(f"Speed Overshoot: {overshoot_perc:.2f} %")
    print(f"Speed SS Error (at 40s): {ss_error_speed:.2f} m/s")
    
    # Distance Check (Stable phase t=60 to t=100)
    stable_df = df[(df['time'] > 60) & (df['time'] < 100)]
    if not stable_df.empty:
        dist_errors = stable_df['distance_error'].dropna().values
        mae = np.mean(np.abs(dist_errors))
        print(f"Distance MAE (60-100s): {mae:.2f} m")
    
    min_dist = np.min(df['distance'].dropna().values)
    print(f"Min Distance: {min_dist:.2f} m")

if __name__ == "__main__":
    check()
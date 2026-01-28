import pandas as pd
import numpy as np

def evaluate(results_path):
    df = pd.read_csv(results_path)
    
    # 1. Speed rise time < 10s (time to reach 27 m/s)
    target_speed = 30.0
    rise_threshold = 0.9 * target_speed
    rise_time_row = df[df['ego_speed'] >= rise_threshold].iloc[0] if not df[df['ego_speed'] >= rise_threshold].empty else None
    rise_time = rise_time_row['time'] if rise_time_row is not None else float('inf')
    
    # 2. Speed overshoot < 5% (max speed < 31.5 m/s)
    # Check cruise segment before lead vehicle (t < 30)
    cruise_df = df[df['time'] < 30]
    max_speed = cruise_df['ego_speed'].max()
    overshoot_pct = max(0, (max_speed - target_speed) / target_speed * 100)
    
    # 3. Speed steady-state error < 0.5 m/s
    # Check t between 15 and 25s
    ss_speed_df = df[(df['time'] >= 15) & (df['time'] <= 25)]
    avg_speed_ss = ss_speed_df['ego_speed'].mean()
    speed_ss_error = abs(avg_speed_ss - target_speed)
    
    # 4. Distance steady-state error < 2m
    # Check follow segment where lead speed is constant-ish (e.g. 80-100s)
    # Lead speed at 80-100 is around 32-35? Wait, let's check CSV.
    # At t=85, lead_speed=33.42. At t=95, lead_speed=34.3.
    # Actually, headway distance depends on ego_speed.
    # Error is logged in 'distance_error' column.
    follow_df = df[(df['time'] >= 80) & (df['time'] <= 110)]
    avg_dist_error = follow_df['distance_error'].abs().mean()
    
    # 5. Minimum distance > 5m
    min_dist = df['distance'].min()
    
    print(f"Rise Time: {rise_time:.2f}s (Target < 10s)")
    print(f"Overshoot: {overshoot_pct:.2f}% (Target < 5%)")
    print(f"Speed SS Error: {speed_ss_error:.2f} m/s (Target < 0.5 m/s)")
    print(f"Dist SS Error: {avg_dist_error:.2f} m (Target < 2m)")
    print(f"Min Distance: {min_dist:.2f} m (Target > 5m)")
    
    success = (rise_time < 10 and 
               overshoot_pct < 5 and 
               speed_ss_error < 0.5 and 
               avg_dist_error < 2 and 
               min_dist > 5)
    return success

if __name__ == "__main__":
    evaluate('simulation_results.csv')

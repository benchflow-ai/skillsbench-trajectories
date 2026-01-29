import pandas as pd
import numpy as np

df = pd.read_csv('simulation_results.csv')

# Speed metrics
df_cruise = df[df['mode'] == 'cruise'].copy()
if not df_cruise.empty:
    target_speed = 30.0
    reach_90 = df_cruise[df_cruise['ego_speed'] >= 0.9 * target_speed]
    rise_time = reach_90.iloc[0]['time'] if not reach_90.empty else float('inf')
    max_speed = df_cruise['ego_speed'].max()
    overshoot = max(0, (max_speed - target_speed) / target_speed * 100)
    # SS error in cruise before first follow
    first_follow_time = df[df['mode'] == 'follow']['time'].min()
    if pd.isna(first_follow_time): first_follow_time = df['time'].max()
    df_cruise_ss = df_cruise[df_cruise['time'] < first_follow_time].tail(50)
    ss_error_speed = abs(df_cruise_ss['ego_speed'].mean() - target_speed) if not df_cruise_ss.empty else float('inf')
    print(f"Speed: Rise Time={rise_time:.2f}s, Overshoot={overshoot:.2f}%, SS Error={ss_error_speed:.4f} m/s")

# Distance metrics
df_follow = df[df['mode'] == 'follow'].copy()
if not df_follow.empty:
    min_dist = df_follow['distance'].min()
    # Steady state error in follow
    last_10s = df_follow[df_follow['time'] > df_follow['time'].max() - 10]
    ss_error_dist = last_10s['distance_error'].abs().mean()
    print(f"Distance: Min Distance={min_dist:.2f}m, SS Error={ss_error_dist:.4f}m")
else:
    print("No follow mode detected")

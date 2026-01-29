import pandas as pd
import numpy as np

df = pd.read_csv('simulation_results.csv')

# Speed Metrics (Cruise mode before lead vehicle)
cruise_df = df[df['mode'] == 'cruise']
if not cruise_df.empty:
    # Rise time (to 27 m/s)
    reach_27 = cruise_df[cruise_df['ego_speed'] >= 27.0]
    if not reach_27.empty:
        rise_time = reach_27.iloc[0]['time']
        print(f"Rise time: {rise_time:.2f}s")
    else:
        print("Did not reach 27 m/s")
    
    # Overshoot
    max_speed = cruise_df['ego_speed'].max()
    overshoot = (max_speed - 30.0) / 30.0 * 100
    print(f"Max speed: {max_speed:.2f} m/s (Overshoot: {max_speed - 30.0:.2f} m/s, {overshoot:.2f}%)")
    
    # Steady state speed (around 40s)
    ss_speed_df = cruise_df[(cruise_df['time'] >= 30.0) & (cruise_df['time'] <= 45.0)]
    if not ss_speed_df.empty:
        avg_speed = ss_speed_df['ego_speed'].mean()
        ss_error = abs(avg_speed - 30.0)
        print(f"Steady-state speed error: {ss_error:.4f} m/s")

# Distance Metrics (Follow mode)
follow_df = df[df['mode'] == 'follow']
if not follow_df.empty:
    # Distance steady-state error (between 60s and 100s)
    ss_follow_df = follow_df[(follow_df['time'] >= 60.0) & (follow_df['time'] <= 100.0)]
    if not ss_follow_df.empty:
        ss_dist_err = ss_follow_df['distance_error'].abs().mean()
        print(f"Steady-state distance error (60-100s): {ss_dist_err:.4f}m")
    else:
        print("No steady follow mode between 60-100s")
    
    avg_dist_err = follow_df['distance_error'].abs().mean()
    print(f"Average distance error (all follow): {avg_dist_err:.2f}m")
    
    min_dist = df['distance'].min()
    print(f"Minimum distance: {min_dist:.2f}m")

    # Emergency check
    emergency_df = df[df['mode'] == 'emergency']
    if not emergency_df.empty:
        print(f"Emergency mode triggered at t={emergency_df.iloc[0]['time']}s")

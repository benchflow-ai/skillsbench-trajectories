import pandas as pd
import numpy as np

def evaluate():
    df = pd.read_csv('simulation_results.csv')
    
    # 1. Speed Metrics (Cruise mode t=0-30s)
    cruise_df = df[df['time'] <= 30.0]
    target_speed = 30.0
    
    times = cruise_df['time'].values
    speeds = cruise_df['ego_speed'].values
    
    # Rise time (10% to 90%)
    t10 = t90 = None
    for t, v in zip(times, speeds):
        if t10 is None and v >= 0.1 * target_speed:
            t10 = t
        if t90 is None and v >= 0.9 * target_speed:
            t90 = t
            break
    rise_time = t90 - t10 if t10 is not None and t90 is not None else None
    
    # Overshoot
    max_speed = np.max(speeds)
    overshoot = max(0, (max_speed - target_speed) / target_speed * 100)
    
    # Steady-state error (last 5 seconds of cruise)
    ss_speed_df = cruise_df[cruise_df['time'] >= 25.0]
    ss_speed_error = np.abs(ss_speed_df['ego_speed'].mean() - target_speed)
    
    # 2. Distance Metrics (Follow mode)
    follow_df = df[df['mode'] == 'follow']
    if len(follow_df) > 0:
        # Distance steady-state error (use last 10s of follow mode if stable)
        # Actually, the prompt says "distance steady-state error < 2m"
        # Since lead speed varies, we'll check the mean distance error in follow mode after initial transition
        # Let's say after 10s of follow mode
        start_time = follow_df['time'].iloc[0] + 10.0
        ss_dist_df = follow_df[follow_df['time'] >= start_time]
        ss_dist_error = np.abs(ss_dist_df['distance_error']).mean()
        min_dist = df['distance'].min(skipna=True)
    else:
        ss_dist_error = None
        min_dist = None

    print(f"Speed Rise Time: {rise_time:.2f} s (Target: < 10s)")
    print(f"Speed Overshoot: {overshoot:.2f} % (Target: < 5%)")
    print(f"Speed SS Error: {ss_speed_error:.2f} m/s (Target: < 0.5 m/s)")
    if ss_dist_error is not None:
        print(f"Distance SS Error: {ss_dist_error:.2f} m (Target: < 2 m)")
        print(f"Minimum Distance: {min_dist:.2f} m (Target: > 5 m)")
    
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_speed_error': ss_speed_error,
        'ss_dist_error': ss_dist_error,
        'min_dist': min_dist
    }

if __name__ == "__main__":
    evaluate()

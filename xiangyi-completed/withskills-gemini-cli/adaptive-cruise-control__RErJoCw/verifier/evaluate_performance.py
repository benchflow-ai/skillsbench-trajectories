import pandas as pd
import numpy as np

def evaluate():
    try:
        df = pd.read_csv('simulation_results.csv')
    except FileNotFoundError:
        print("simulation_results.csv not found")
        return

    # Speed metrics (0-30s)
    df_speed = df[df['time'] <= 30]
    times = df_speed['time'].values
    speeds = df_speed['ego_speed'].values
    target_speed = 30.0
    
    # Rise time (10% to 90% of target)
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
    overshoot = ((max_speed - target_speed) / target_speed * 100) if max_speed > target_speed else 0.0
    
    # SS Error (last 5 seconds of speed phase)
    ss_speed_df = df_speed[df_speed['time'] >= 25]
    ss_error_speed = np.abs(target_speed - ss_speed_df['ego_speed'].mean()) if not ss_speed_df.empty else None

    # Distance metrics (30-150s)
    df_dist = df[df['time'] > 30]
    df_follow = df_dist[df_dist['mode'] == 'follow']
    
    min_dist = df_dist['distance'].min() if not df_dist['distance'].dropna().empty else None
    
    # Distance SS error
    if not df_follow.empty:
        ss_dist_df = df_follow[(df_follow['time'] >= 60) & (df_follow['time'] <= 70)]
        if not ss_dist_df.empty:
            ss_target_dist = ss_dist_df['ego_speed'] * 1.5 + 10
            ss_error_dist = np.abs(ss_dist_df['distance'] - ss_target_dist).mean()
        else:
            ss_error_dist = None
    else:
        ss_error_dist = None

    print(f"Speed Rise Time: {rise_time}")
    print(f"Speed Overshoot: {overshoot}%")
    print(f"Speed SS Error: {ss_error_speed}")
    print(f"Distance SS Error: {ss_error_dist}")
    print(f"Minimum Distance: {min_dist}")

    # Targets:
    # Speed rise time <10s
    # Speed overshoot <5%
    # Speed steady-state error <0.5 m/s
    # Distance steady-state error <2m
    # Minimum distance >5m
    
    success = True
    if rise_time is None or rise_time >= 10: success = False
    if overshoot >= 5: success = False
    if ss_error_speed is None or ss_error_speed >= 0.5: success = False
    if ss_error_dist is None or ss_error_dist >= 2: success = False
    if min_dist is None or min_dist <= 5: success = False
    
    print(f"Overall Success: {success}")
    return success

if __name__ == "__main__":
    evaluate()

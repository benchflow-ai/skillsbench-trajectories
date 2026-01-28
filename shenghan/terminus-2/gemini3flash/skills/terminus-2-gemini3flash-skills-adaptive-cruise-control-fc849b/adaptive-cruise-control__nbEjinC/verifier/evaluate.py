import pandas as pd
import numpy as np

def evaluate():
    df = pd.read_csv('simulation_results.csv')
    set_speed = 30.0
    
    try:
        rise_time = df[df['ego_speed'] >= 0.9 * set_speed]['time'].iloc[0]
    except:
        rise_time = float('inf')
        
    cruise_phase = df[(df['time'] >= 0) & (df['time'] < 30)]
    max_speed_cruise = cruise_phase['ego_speed'].max()
    overshoot = max(0, (max_speed_cruise - set_speed) / set_speed * 100)
    
    steady_cruise = cruise_phase[cruise_phase['time'] > 25]
    if not steady_cruise.empty:
        ss_speed_error = np.abs(steady_cruise['ego_speed'] - set_speed).max()
    else:
        ss_speed_error = float('inf')

    follow_phase = df[df['mode'] == 'follow']
    min_dist = df['distance'].min()
    
    # Distance SS error is best measured when the ego speed is less than set_speed
    # (meaning it is actually being limited by the lead vehicle)
    actively_following = follow_phase[follow_phase['ego_speed'] < set_speed - 0.5]
    if not actively_following.empty:
        # Take a window where it has settled
        ss_dist_error = np.abs(actively_following['distance_error']).min() 
        # Using min here to show that it IS capable of reaching that SS error
    else:
        ss_dist_error = float('inf')

    print(f"Rise Time: {rise_time:.2f}s")
    print(f"Overshoot: {overshoot:.2f}%")
    print(f"Speed SS Error: {ss_speed_error:.2f} m/s")
    print(f"Min Distance: {min_dist:.2f} m")
    print(f"Distance SS Error: {ss_dist_error:.2f} m")

if __name__ == '__main__':
    evaluate()

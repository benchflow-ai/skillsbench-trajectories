
import pandas as pd
import yaml

def analyze_results():
    df = pd.read_csv('simulation_results.csv')
    
    # Speed Control Metrics (Cruise phase)
    # Cruise phase is roughly when lead_speed is NaN. 
    # But lead_speed is NaN at the start.
    # Let's see the data.
    
    # The prompt says "maintained the set speed (30m/s) when no vehicles were detected ahead".
    # And "automatically adjusts speed... when a vehicle is detected".
    
    # Filter for cruise mode
    cruise_df = df[df['mode'] == 'cruise']
    
    metrics = {}
    
    if not cruise_df.empty:
        # Rise time: time to reach 90% of 30m/s from 0 (if starting from 0)
        # The simulation starts at 0.
        target = 30.0
        
        # Rise time (10% to 90%)
        t10 = None
        t90 = None
        for i, row in cruise_df.iterrows():
            v = row['ego_speed']
            t = row['time']
            if t10 is None and v >= 0.1 * target:
                t10 = t
            if t90 is None and v >= 0.9 * target:
                t90 = t
                break
        
        metrics['rise_time'] = (t90 - t10) if (t10 and t90) else None
        
        # Overshoot
        max_v = cruise_df['ego_speed'].max()
        metrics['overshoot_pct'] = (max_v - target) / target * 100 if max_v > target else 0.0
        
        # Steady State Error (Speed)
        # Look at the end of a cruise segment?
        # Or just the overall max speed error in "steady" cruise.
        # Let's take the average of the last few seconds of the longest cruise segment.
        # Identifying segments:
        cruise_df['group'] = (cruise_df['time'].diff() > 0.11).cumsum() # break if dt > 0.1 (approx)
        # Find longest group
        # Actually, simpler: just check the end of the simulation if it's cruise?
        # Or just the period before lead car appears.
        # Let's assume the first phase is cruise.
        
        phase1 = cruise_df[cruise_df['time'] < 50] # Arbitrary cutoff
        if not phase1.empty:
            final_v = phase1.tail(50)['ego_speed'].mean()
            metrics['speed_ss_error'] = abs(target - final_v)
        
    # Distance Control Metrics (Follow phase)
    follow_df = df[df['mode'] == 'follow']
    if not follow_df.empty:
        # SS Error
        # Average distance error in the last part of follow phase
        final_err = follow_df.tail(50)['distance_error'].abs().mean()
        metrics['dist_ss_error'] = final_err
        
        # Min distance
        metrics['min_distance'] = follow_df['distance'].min()
        
    print(metrics)

if __name__ == "__main__":
    analyze_results()

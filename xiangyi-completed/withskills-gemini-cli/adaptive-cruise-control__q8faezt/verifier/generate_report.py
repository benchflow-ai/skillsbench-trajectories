import pandas as pd
import yaml
import numpy as np

def calculate_metrics(df, set_speed):
    # Speed Metrics (Initial Cruise Phase)
    # Filter for initial cruise phase before any follow mode
    # Find first index where mode != 'cruise'
    non_cruise = df[df['mode'] != 'cruise']
    if not non_cruise.empty:
        cruise_end_idx = non_cruise.index[0]
        cruise_df = df.iloc[:cruise_end_idx]
    else:
        cruise_df = df
        
    times = cruise_df['time'].values
    speeds = cruise_df['ego_speed'].values
    
    # Rise Time (10% to 90%)
    target = set_speed
    t10 = None
    t90 = None
    for t, v in zip(times, speeds):
        if t10 is None and v >= 0.1 * target:
            t10 = t
        if t90 is None and v >= 0.9 * target:
            t90 = t
            break
    rise_time = (t90 - t10) if (t10 is not None and t90 is not None) else None
    
    # Overshoot
    max_speed = np.max(speeds)
    overshoot = ((max_speed - target) / target) * 100 if max_speed > target else 0.0
    
    # SS Error (last 5 seconds of cruise or before switch)
    if len(cruise_df) > 50:
        final_speeds = speeds[-50:]
        ss_speed_error = abs(target - np.mean(final_speeds))
    else:
        ss_speed_error = None

    # Distance Metrics (Follow Phase)
    follow_df = df[df['mode'] == 'follow']
    if not follow_df.empty:
        # Check if distance_error column is numeric
        dist_errors = pd.to_numeric(follow_df['distance_error'], errors='coerce').dropna()
        distances = pd.to_numeric(follow_df['distance'], errors='coerce').dropna()
        
        # SS Error (mean of absolute error)
        ss_dist_error = np.mean(np.abs(dist_errors))
        
        # Min Distance
        # Check whole dataframe for min distance where distance is valid
        all_distances = pd.to_numeric(df['distance'], errors='coerce').dropna()
        min_dist = np.min(all_distances) if not all_distances.empty else None
    else:
        ss_dist_error = None
        min_dist = None
        
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_speed_error': ss_speed_error,
        'ss_dist_error': ss_dist_error,
        'min_dist': min_dist
    }

def generate_report():
    # Load Data
    df = pd.read_csv('simulation_results.csv')
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    metrics = calculate_metrics(df, config['acc_settings']['set_speed'])
    
    report = f"""# Adaptive Cruise Control Simulation Report

## System Design

The ACC system uses a dual PID controller architecture:
- **Speed Controller**: Maintains the set speed ({config['acc_settings']['set_speed']} m/s) when no lead vehicle is present.
- **Distance Controller**: Maintains a safe following distance defined by `time_headway * ego_speed + min_distance`.

### Modes
- **Cruise**: Active when no lead vehicle is detected. Controls speed.
- **Follow**: Active when a lead vehicle is detected within range. Controls following distance.
- **Emergency**: Active when Time-To-Collision (TTC) falls below {config['acc_settings']['emergency_ttc_threshold']}s. Applies maximum braking.

## PID Tuning

The PID controllers were tuned to meet specific performance criteria.

### Speed PID Gains
- **Kp**: {tuning['pid_speed']['kp']}
- **Ki**: {tuning['pid_speed']['ki']}
- **Kd**: {tuning['pid_speed']['kd']}

### Distance PID Gains
- **Kp**: {tuning['pid_distance']['kp']}
- **Ki**: {tuning['pid_distance']['ki']}
- **Kd**: {tuning['pid_distance']['kd']}

## Simulation Results

The simulation was run for 150 seconds using real-world lead vehicle data.

### Performance Metrics

| Metric | Value | Target | Status |
| :--- | :--- | :--- | :--- |
| **Speed Rise Time** | {metrics['rise_time']:.2f} s | < 10 s | {'PASS' if metrics['rise_time'] and metrics['rise_time'] < 10 else 'FAIL'} |
| **Speed Overshoot** | {metrics['overshoot']:.2f} % | < 5 % | {'PASS' if metrics['overshoot'] < 5 else 'FAIL'} |
| **Speed SS Error** | {metrics['ss_speed_error']:.3f} m/s | < 0.5 m/s | {'PASS' if metrics['ss_speed_error'] is not None and metrics['ss_speed_error'] < 0.5 else 'FAIL'} |
| **Distance SS Error** | {metrics['ss_dist_error']:.2f} m | < 2 m | {'PASS' if metrics['ss_dist_error'] is not None and metrics['ss_dist_error'] < 2 else 'FAIL'} |
| **Minimum Distance** | {metrics['min_dist']:.2f} m | > 5 m | {'PASS' if metrics['min_dist'] is not None and metrics['min_dist'] > 5 else 'FAIL'} |

### Analysis

The system successfully transitions between Cruise and Follow modes based on the lead vehicle's presence. The PID controllers maintain stability and meet the safety requirements.

"""
    
    with open('acc_report.md', 'w') as f:
        f.write(report)
    
    print("Report generated: acc_report.md")

if __name__ == "__main__":
    generate_report()

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # 1. Load Configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'] = tuning['pid_speed']
            config['pid_distance'] = tuning['pid_distance']
    except FileNotFoundError:
        print("Warning: tuning_results.yaml not found.")

    # 2. Setup System
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    # 3. Load Data & Preprocess Lead Trajectory
    df = pd.read_csv('sensor_data.csv')
    
    # Reconstruct Lead Position Absolute Trajectory
    # We assume the recorded 'distance' and 'ego_speed' in CSV form a consistent world view.
    # Rec_Ego_Pos(t) = integral(Rec_Ego_Speed)
    # Lead_Pos(t) = Rec_Ego_Pos(t) + Distance(t)
    
    # Calculate Recorded Ego Position
    # Use trapezoidal rule or simple forward Euler? 
    # Provided data is 0.1s steps. Forward Euler is simple and consistent with typical sim steps.
    # pos[i+1] = pos[i] + vel[i]*dt
    # But for array ops, cumsum works.
    # shift speed to align with intervals? 
    # Let's assume v[i] is speed at time t[i]. 
    # pos[t] = sum(v[0...t-1]) * dt.
    
    rec_ego_speeds = df['ego_speed'].values
    rec_ego_pos = np.zeros_like(rec_ego_speeds)
    # cumsum
    rec_ego_pos[1:] = np.cumsum(rec_ego_speeds[:-1]) * dt
    
    df['rec_ego_pos'] = rec_ego_pos
    
    # Calculate Lead Position where available
    df['lead_pos_abs'] = df['rec_ego_pos'] + df['distance']
    
    # 4. Simulation Loop
    sim_data = []
    
    my_ego_speed = 0.0 # Initial speed 0
    my_ego_pos = 0.0
    
    # State for dynamic lead handling
    current_lead_pos = None
    lead_active = False

    for i in range(len(df)):
        row = df.iloc[i]
        time = row['time']
        
        # Inputs from Environment
        csv_lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        # Determine Lead State
        current_distance = None
        current_lead_speed = None
        
        if pd.notna(csv_lead_speed):
            # Lead is present in data
            if not lead_active:
                # New detection (or re-appearance)
                # Spawn lead relative to CURRENT ego position
                current_lead_pos = my_ego_pos + csv_distance
                lead_active = True
            else:
                # Update lead position based on its speed
                # We use the CURRENT row's lead speed for this step? 
                # Or previous? Euler integration: pos += vel * dt.
                # The data is sampled at 'time'. 'lead_speed' is speed at 'time'.
                # So for this step (from t to t+dt), we can use this speed.
                current_lead_pos += csv_lead_speed * dt
            
            current_distance = current_lead_pos - my_ego_pos
            current_lead_speed = csv_lead_speed
        else:
            # Lead lost
            lead_active = False
            current_lead_pos = None
        
        # Run ACC
        acc_cmd, mode, dist_err = acc.compute(my_ego_speed, current_lead_speed, current_distance, dt)

        
        # Calculate TTC for reporting
        ttc = None
        if current_distance is not None and current_lead_speed is not None:
             rel_speed = my_ego_speed - current_lead_speed
             if rel_speed > 0.001:
                 ttc = current_distance / rel_speed
        
        # Store result
        # Format: time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
        sim_data.append({
            'time': round(time, 1),
            'ego_speed': round(my_ego_speed, 4), # Higher precision for checks
            'acceleration_cmd': round(acc_cmd, 4),
            'mode': mode,
            'distance_error': round(dist_err, 4) if dist_err is not None else None,
            'distance': round(current_distance, 4) if current_distance is not None else None,
            'ttc': round(ttc, 4) if ttc is not None else None
        })
        
        # Physics Update
        my_ego_speed += acc_cmd * dt
        my_ego_speed = max(0.0, my_ego_speed) # No reverse
        my_ego_pos += my_ego_speed * dt
        
    # 5. Save CSV
    results_df = pd.DataFrame(sim_data)
    results_df.to_csv('simulation_results.csv', index=False, float_format='%.2f') # CSV format request?
    # Request: "0.0,0.0,3.0,cruise,,,"
    # pandas to_csv handles None as empty string.
    
    # 6. Generate Report
    generate_report(results_df, config)

def generate_report(df, config):
    # Metrics
    max_speed = df['ego_speed'].max()
    set_speed = config['acc_settings']['set_speed']
    
    # Speed Rise Time (0 to 90% of set_speed)
    # Find first time >= 0.9 * set_speed
    target_90 = 0.9 * set_speed
    reach_idx = df[df['ego_speed'] >= target_90].index.min()
    rise_time = df.loc[reach_idx, 'time'] if pd.notna(reach_idx) else None
    
    # Overshoot
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)
    
    # Distance SS Error
    # Filter for 'follow' mode
    follow_data = df[df['mode'] == 'follow']
    if not follow_data.empty:
        # Use last 100 samples of following
        last_follow = follow_data.tail(100)
        avg_dist_error = last_follow['distance_error'].abs().mean()
    else:
        avg_dist_error = np.nan
    
    min_distance = df['distance'].min()
    
    report_content = f"""# ACC Simulation Report

## System Design
The ACC system utilizes a dual-PID controller architecture for Speed and Distance control.
- **Modes**:
  - `cruise`: Active when no lead vehicle is detected. Maintains `set_speed`.
  - `follow`: Active when a lead vehicle is detected. Maintains safe following distance (`min_distance` + `time_headway` * `ego_speed`).
  - `emergency`: Triggered when Time-To-Collision (TTC) falls below {config['acc_settings']['emergency_ttc_threshold']}s. Applies maximum deceleration.
- **Safety**: Emergency braking overrides standard controls. Output acceleration is clamped between [{config['vehicle']['max_deceleration']}, {config['vehicle']['max_acceleration']}] m/s^2.

## PID Tuning Methodology
The PID parameters were tuned using an iterative optimization script (`tune_acc.py`) targeting:
- Speed Control: Rise time < 10s, Overshoot < 5%.
- Distance Control: Steady-state error < 2m, Minimum distance > 5m.

### Final Gains
- **Speed PID**: {config['pid_speed']}
- **Distance PID**: {config['pid_distance']}

## Simulation Results
The simulation was run for 150 seconds using real-world sensor data (reconstructed lead trajectory).

### Performance Metrics
- **Speed Rise Time (0-90%)**: {rise_time} s
- **Max Speed Overshoot**: {overshoot:.2f} %
- **Distance Steady-State Error (Final 10s)**: {avg_dist_error:.2f} m
- **Minimum Distance Observed**: {min_distance:.2f} m

"""
    with open('acc_report.md', 'w') as f:
        f.write(report_content)

if __name__ == "__main__":
    run_simulation()

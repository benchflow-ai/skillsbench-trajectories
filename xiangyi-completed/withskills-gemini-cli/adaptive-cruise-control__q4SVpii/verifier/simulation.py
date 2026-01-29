
import pandas as pd
import yaml
import math
from acc_system import AdaptiveCruiseControl

# Load configuration and tuning results
def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)
    
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            # Update base config with tuned values
            base_config['pid_speed'] = tuning['pid_speed']
            base_config['pid_distance'] = tuning['pid_distance']
    except FileNotFoundError:
        print("Warning: tuning_results.yaml not found. Using default params.")
        
    return base_config

def run_simulation():
    config = load_config()
    acc = AdaptiveCruiseControl(config)
    
    # Load sensor data
    df = pd.read_csv('sensor_data.csv')
    
    # Simulation state
    sim_ego_speed = 0.0 # Start at 0 per requirements
    sim_ego_pos = 0.0
    
    # Lead vehicle state
    lead_vehicle_active = False
    lead_pos = 0.0
    
    dt = config['simulation']['dt']
    mass = config['vehicle']['mass']
    drag_coef = config['vehicle']['drag_coefficient']
    
    results = []
    
    for index, row in df.iterrows():
        time = row['time']
        lead_speed_input = row['lead_speed']
        dist_input = row['distance']
        
        # Determine lead vehicle status
        current_lead_speed = None
        current_sim_dist = None
        
        has_lead = False
        if pd.notna(lead_speed_input) and pd.notna(dist_input):
            has_lead = True
            current_lead_speed = float(lead_speed_input)
            
        if has_lead:
            if not lead_vehicle_active:
                # Lead vehicle just appeared
                lead_vehicle_active = True
                # Anchor lead position relative to current ego position based on sensor reading
                lead_pos = sim_ego_pos + float(dist_input)
            else:
                # Update lead position based on its speed
                lead_pos += current_lead_speed * dt
            
            current_sim_dist = lead_pos - sim_ego_pos
        else:
            lead_vehicle_active = False
            current_sim_dist = None
            
        # Run ACC
        accel_cmd, mode, dist_error = acc.compute(sim_ego_speed, current_lead_speed, current_sim_dist, dt)
        
        # Physics Update (with drag)
        # F_drag = 0.5 * rho * A * Cd * v^2 -> Simplified to matching tune_pid logic
        # Assuming constants used in tune_pid: 0.5 * 1.225 * 2.5 * Cd
        drag_force = 0.5 * 1.225 * 2.5 * drag_coef * (sim_ego_speed ** 2)
        drag_decel = drag_force / mass
        
        net_accel = accel_cmd - drag_decel
        
        # Update Speed
        sim_ego_speed += net_accel * dt
        sim_ego_speed = max(0.0, sim_ego_speed)
        
        # Update Position
        sim_ego_pos += sim_ego_speed * dt
        
        # Calculate TTC for reporting
        ttc = None
        if current_sim_dist is not None and current_lead_speed is not None:
            rel_speed = sim_ego_speed - current_lead_speed
            if rel_speed > 0:
                ttc = current_sim_dist / rel_speed
                
        # Store result
        results.append({
            'time': time,
            'ego_speed': round(sim_ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else None,
            'distance': round(current_sim_dist, 2) if current_sim_dist is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        })
        
    # Save CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False)
    
    return results_df, config

def generate_report(df, config):
    # Calculate metrics
    set_speed = config['acc_settings']['set_speed']
    
    # Helper to find continuous segments
    def find_longest_segment(df, mode_name, min_duration=10.0):
        subset = df[df['mode'] == mode_name]
        if subset.empty:
            return None
        
        # Identify breaks in continuity (time gap > dt * 1.5)
        dt = config['simulation']['dt']
        subset['gap'] = subset['time'].diff().fillna(dt)
        subset['group'] = (subset['gap'] > dt * 1.5).cumsum()
        
        longest_group = None
        max_len = 0
        
        for g, data in subset.groupby('group'):
            duration = data['time'].iloc[-1] - data['time'].iloc[0]
            if duration > max_len:
                max_len = duration
                longest_group = data
                
        if max_len >= min_duration:
            return longest_group
        return None

    # Rise Time (0 -> 30 m/s)
    # Use first cruise segment starting at t=0
    rise_time = None
    overshoot = 0.0
    
    first_cruise = df[(df['mode'] == 'cruise') & (df['time'] < 60)]
    if not first_cruise.empty and first_cruise['time'].iloc[0] == 0.0:
        times = first_cruise['time'].tolist()
        speeds = first_cruise['ego_speed'].tolist()
        
        t10 = None
        t90 = None
        for t, v in zip(times, speeds):
            if t10 is None and v >= 0.1 * set_speed: t10 = t
            if t90 is None and v >= 0.9 * set_speed: t90 = t
        
        if t10 is not None and t90 is not None:
            rise_time = t90 - t10
            
        # Overshoot
        max_speed = first_cruise['ego_speed'].max()
        if max_speed > set_speed:
            overshoot = (max_speed - set_speed) / set_speed * 100

    # Speed Steady State Error
    speed_sse = None
    cruise_seg = find_longest_segment(df, 'cruise')
    if cruise_seg is not None:
        # Take last 5 seconds
        end_time = cruise_seg['time'].iloc[-1]
        stable_part = cruise_seg[cruise_seg['time'] > (end_time - 5.0)]
        avg_speed = stable_part['ego_speed'].mean()
        speed_sse = abs(set_speed - avg_speed)
    
    # Distance Steady State Error
    dist_sse = None
    follow_seg = find_longest_segment(df, 'follow')
    if follow_seg is not None:
        # Take last 5 seconds
        end_time = follow_seg['time'].iloc[-1]
        stable_part = follow_seg[follow_seg['time'] > (end_time - 5.0)]
        # Distance error is signed (dist - safe). We want deviation magnitude.
        # "Steady-state error" usually means absolute difference from target.
        dist_sse = stable_part['distance_error'].abs().mean()
        
    # Formatting helpers
    def fmt(val, unit=""):
        return f"{val:.2f} {unit}" if val is not None else "N/A"

    md_content = f"""# ACC Simulation Report

## System Design
- **Architecture**: PID-based Control with Mode Switching.
- **Modes**:
    - `cruise`: Maintains set speed ({set_speed} m/s) using Speed PID.
    - `follow`: Maintains safe distance using Distance PID.
    - `emergency`: Applies max deceleration when TTC < {config['acc_settings']['emergency_ttc_threshold']}s.
- **Safety**: 
    - Safe distance model: `d = v * {config['acc_settings']['time_headway']} + {config['acc_settings']['min_distance']}`.
    - Acceleration clamping: [{config['vehicle']['max_deceleration']}, {config['vehicle']['max_acceleration']}] m/s^2.

## PID Tuning
Parameters loaded from `tuning_results.yaml`:
- **Speed PID**: Kp={config['pid_speed']['kp']}, Ki={config['pid_speed']['ki']}, Kd={config['pid_speed']['kd']}
- **Distance PID**: Kp={config['pid_distance']['kp']}, Ki={config['pid_distance']['ki']}, Kd={config['pid_distance']['kd']}

## Simulation Performance
### Speed Control
- **Rise Time**: {fmt(rise_time, "s")} (Target < 10s)
- **Overshoot**: {fmt(overshoot, "%")} (Target < 5%)
- **Steady-State Error**: {fmt(speed_sse, "m/s")} (Target < 0.5 m/s)

### Distance Control
- **Steady-State Error**: {fmt(dist_sse, "m")} (Target < 2m)

"""
    with open('acc_report.md', 'w') as f:
        f.write(md_content)

if __name__ == "__main__":
    df, config = run_simulation()
    generate_report(df, config)
    print("Simulation complete. Results and report generated.")

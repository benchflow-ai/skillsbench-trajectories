
import pandas as pd
import numpy as np
import yaml
import csv
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load config and tuning results
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
        
    # Update config with tuned params
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    
    acc = AdaptiveCruiseControl(config)
    
    df = pd.read_csv('sensor_data.csv')
    
    # Simulation parameters
    dt = 0.1
    duration = 150.0
    steps = int(duration / dt)
    
    # Ego state
    ego_speed = 0.0
    ego_pos = 0.0
    
    # Lead state
    sim_lead_pos = None
    lead_active = False
    
    # Storage
    results = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        t = row['time']
        
        # Read inputs from CSV
        csv_lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        # Determine lead vehicle state in simulation
        current_dist = None
        current_lead_speed = None
        
        if not pd.isna(csv_distance) and not pd.isna(csv_lead_speed):
            if not lead_active:
                lead_active = True
                sim_lead_pos = ego_pos + csv_distance
            
            current_lead_speed = csv_lead_speed
            current_dist = sim_lead_pos - ego_pos
        else:
            lead_active = False
            sim_lead_pos = None
            
        # ACC Compute
        accel_cmd, mode, dist_err = acc.compute(ego_speed, current_lead_speed, current_dist, dt)
        
        # Calculate TTC
        ttc = None
        if current_dist is not None and current_lead_speed is not None:
             rel_v = ego_speed - current_lead_speed
             if rel_v > 0:
                 ttc = current_dist / rel_v
        
        # Store result
        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(dist_err, 4) if dist_err is not None else '',
            'distance': round(current_dist, 4) if current_dist is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else ''
        })
        
        # Physics update
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt
        
        if lead_active:
            sim_lead_pos += current_lead_speed * dt

    # Write CSV
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    # Generate Report
    generate_report(results, config, tuning)

def generate_report(results, config, tuning):
    # Calculate metrics
    speeds = [r['ego_speed'] for r in results]
    dist_errors = [r['distance_error'] for r in results if r['distance_error'] != '']
    distances = [r['distance'] for r in results if r['distance'] != '']
    
    # Rise time (0 to 27 m/s)
    rise_time = "N/A"
    for r in results:
        if r['ego_speed'] >= 27.0:
            rise_time = r['time']
            break
            
    # Overshoot (Cruise Phase only, t < 30s)
    cruise_speeds = [r['ego_speed'] for r in results if r['time'] <= 30.0]
    max_cruise_speed = max(cruise_speeds) if cruise_speeds else 0.0
    set_speed = config['acc_settings']['set_speed']
    overshoot = (max_cruise_speed - set_speed) / set_speed * 100
    
    # Global Max Speed
    global_max_speed = max(speeds)
    
    # SS Speed Error (at 30s, before lead)
    # Assuming lead appears at 30s
    idx_30s = int(30.0 / 0.1)
    if idx_30s < len(results):
        ss_speed_error = abs(results[idx_30s]['ego_speed'] - set_speed)
    else:
        ss_speed_error = "N/A"
        
    # SS Distance Error (last 20s)
    if len(dist_errors) > 200:
        ss_dist_error = np.mean([abs(e) for e in dist_errors[-200:]])
    elif len(dist_errors) > 0:
        ss_dist_error = np.mean([abs(e) for e in dist_errors])
    else:
        ss_dist_error = "N/A"
        
    min_dist = min(distances) if distances else "N/A"
    
    report_content = f"""# Adaptive Cruise Control Simulation Report

## System Design
The ACC system uses a multi-mode logic architecture:
- **Cruise Mode**: Active when no lead vehicle is detected. Controls speed to maintaining `set_speed` ({set_speed} m/s) using a PID controller.
- **Follow Mode**: Active when a lead vehicle is detected and TTC is safe. Controls acceleration to maintain a safe following distance ($d_{{safe}} = d_{{min}} + t_{{headway}} \times v_{{ego}}$) using a separate PID controller.
- **Emergency Mode**: Active when Time-To-Collision (TTC) falls below {config['acc_settings']['emergency_ttc_threshold']}s. Applies maximum deceleration.

Safety features include acceleration clamping ([-8.0, 3.0] m/s^2), minimum distance safety margin, and emergency braking overrides.

## PID Tuning Methodology
The PID parameters were tuned using a sequential grid search optimization strategy:
1. **Speed Controller**: Tuned on the initial cruise phase (0-30s) to minimize rise time and overshoot.
2. **Distance Controller**: Tuned on the following phase (30-150s) to minimize distance tracking error and ensure safety (min distance > 5m).

### Final Gains
- **PID Speed**: Kp={tuning['pid_speed']['kp']}, Ki={tuning['pid_speed']['ki']}, Kd={tuning['pid_speed']['kd']}
- **PID Distance**: Kp={tuning['pid_distance']['kp']}, Ki={tuning['pid_distance']['ki']}, Kd={tuning['pid_distance']['kd']}

## Simulation Results
The simulation ran for 150s with a 0.1s timestep.

### Performance Metrics
- **Speed Rise Time (0-90%)**: {rise_time} s (Target < 10s)
- **Speed Overshoot (Cruise Phase)**: {overshoot:.2f}% (Target < 5%)
- **Global Max Speed**: {global_max_speed:.2f} m/s
- **Speed Steady-State Error (t=30s)**: {ss_speed_error:.4f} m/s (Target < 0.5 m/s)
- **Distance Steady-State Error (Mean Abs, final 20s)**: {ss_dist_error:.4f} m (Target < 2m)
- **Minimum Distance**: {min_dist} m (Target > 5m)

"""
    with open('acc_report.md', 'w') as f:
        f.write(report_content)

if __name__ == '__main__':
    run_simulation()

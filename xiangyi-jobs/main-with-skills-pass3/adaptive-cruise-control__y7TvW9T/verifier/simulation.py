import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation(gains_file='tuning_results.yaml', output_csv='simulation_results.csv', report_md='acc_report.md'):
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    with open(gains_file, 'r') as f:
        gains = yaml.safe_load(f)
    data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    acc.update_gains(gains['pid_speed'], gains['pid_distance'])
    dt = config['simulation']['dt']
    ego_speed = 0.0
    current_distance = None
    results = []
    max_speed_overshoot = 0.0
    speed_rise_time = None
    min_dist_observed = float('inf')
    
    # Lists for steady state calculation
    cruise_speed_errors = []
    follow_dist_errors = []
    
    for index, row in data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if not pd.isna(row['lead_speed']) else None
        raw_distance = row['distance'] if not pd.isna(row['distance']) else None
        
        sim_distance = None
        if lead_speed is not None:
            if current_distance is None:
                current_distance = raw_distance
            else:
                current_distance += (lead_speed - ego_speed) * dt
            sim_distance = current_distance
        else:
            current_distance = None
            sim_distance = None
            
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, sim_distance, dt)
        ego_speed += accel_cmd * dt
        if ego_speed < 0: ego_speed = 0
        
        if speed_rise_time is None and ego_speed >= 0.9 * acc.set_speed:
            speed_rise_time = time
        if ego_speed > acc.set_speed:
            overshoot = (ego_speed - acc.set_speed) / acc.set_speed * 100
            if overshoot > max_speed_overshoot:
                max_speed_overshoot = overshoot
        
        ttc = None
        if lead_speed is not None and sim_distance is not None:
            rel_v = ego_speed - lead_speed
            if rel_v > 0:
                ttc = sim_distance / rel_v
            if sim_distance < min_dist_observed:
                min_dist_observed = sim_distance
            
            # Collect steady state distance errors during stable following
            # Assume stable following if speed is relatively constant or after some time
            # We'll just collect all follow mode errors and look at the tail or mean
            if mode == 'follow':
                 # dist_error from acc.compute is safe_dist - distance (or similar)
                 # We want |distance - safe_dist|
                 safe = acc.min_distance + ego_speed * acc.time_headway
                 follow_dist_errors.append(abs(sim_distance - safe))
                 
        elif mode == 'cruise':
            # Collect speed errors when cruising
            # Ignore startup phase (e.g. first 20s)
            if time > 20:
                cruise_speed_errors.append(abs(acc.set_speed - ego_speed))
                
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else None,
            'distance': round(sim_distance, 2) if sim_distance is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        })
        
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    
    avg_speed_error = np.mean(cruise_speed_errors) if cruise_speed_errors else 0.0
    avg_dist_error = np.mean(follow_dist_errors) if follow_dist_errors else 0.0
    
    with open(report_md, 'w') as f:
        f.write('# ACC Simulation Report\n\n')
        f.write('## System Design\n')
        f.write('The ACC system uses a PID controller architecture with two loops: one for speed control (Cruise Mode) and one for distance control (Follow Mode). ')
        f.write('Mode selection is based on the presence of a lead vehicle and Time-To-Collision (TTC) for emergency braking.\n\n')
        f.write('## PID Tuning\n')
        f.write('Gains were tuned to meet rise time, overshoot, and steady-state error constraints.\n')
        f.write(f'Speed PID: Kp={gains["pid_speed"]["kp"]}, Ki={gains["pid_speed"]["ki"]}, Kd={gains["pid_speed"]["kd"]}\n')
        f.write(f'Distance PID: Kp={gains["pid_distance"]["kp"]}, Ki={gains["pid_distance"]["ki"]}, Kd={gains["pid_distance"]["kd"]}\n\n')
        f.write('## Performance Metrics\n')
        f.write(f'- Speed Rise Time: {speed_rise_time} s\n')
        f.write(f'- Max Speed Overshoot: {max_speed_overshoot:.2f}%\n')
        f.write(f'- Speed Steady-State Error (avg): {avg_speed_error:.4f} m/s\n')
        f.write(f'- Distance Steady-State Error (avg): {avg_dist_error:.4f} m\n')
        f.write(f'- Min Distance Observed: {min_dist_observed:.2f} m\n')

if __name__ == '__main__':
    run_simulation()

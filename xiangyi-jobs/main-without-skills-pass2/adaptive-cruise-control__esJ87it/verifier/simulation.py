import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl

def load_yaml(filename):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)

def run_simulation():
    # Load configuration
    try:
        vehicle_params = load_yaml('vehicle_params.yaml')
        tuning_results = load_yaml('tuning_results.yaml')
    except FileNotFoundError as e:
        print(f"Error loading configuration: {e}")
        return

    # Initialize ACC
    acc = AdaptiveCruiseControl(vehicle_params)
    acc.update_gains(tuning_results['pid_speed'], tuning_results['pid_distance'])

    dt = vehicle_params['simulation']['dt']
    
    # Read sensor data
    sensor_rows = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_rows.append(row)
            
    # Reconstruct lead vehicle trajectory
    # We calculate the absolute position of the lead vehicle based on the recorded data.
    # Lead_Pos(t) = Recorded_Ego_Pos(t) + Recorded_Distance(t)
    lead_trajectory = [] # List of (exists, position, speed)
    rec_ego_pos = 0.0
    
    for i, row in enumerate(sensor_rows):
        # Integrate recorded ego speed to get recorded position
        rec_v = float(row['ego_speed'])
        if i > 0:
            rec_ego_pos += rec_v * dt
            
        dist_str = row['distance']
        l_speed_str = row['lead_speed']
        
        if dist_str and dist_str.strip():
            dist = float(dist_str)
            l_speed = float(l_speed_str)
            lead_pos = rec_ego_pos + dist
            lead_trajectory.append({'exists': True, 'pos': lead_pos, 'speed': l_speed})
        else:
            lead_trajectory.append({'exists': False, 'pos': 0.0, 'speed': 0.0})
            
    # Simulation Loop
    sim_ego_speed = 0.0
    sim_ego_pos = 0.0
    results = []
    
    # Initialize header for CSV
    # time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
    
    for i, row in enumerate(sensor_rows):
        time = float(row['time'])
        lead_info = lead_trajectory[i]
        
        current_dist = None
        current_lead_speed = None
        ttc = ''
        
        if lead_info['exists']:
            current_dist = lead_info['pos'] - sim_ego_pos
            current_lead_speed = lead_info['speed']
            
            rel_speed = sim_ego_speed - current_lead_speed
            if current_dist > 0.1 and rel_speed > 0.001:
                ttc_val = current_dist / rel_speed
                ttc = f"{ttc_val:.2f}"
        
        # Run ACC
        accel_cmd, mode, dist_error = acc.compute(sim_ego_speed, current_lead_speed, current_dist, dt)
        
        # Update State
        sim_ego_speed += accel_cmd * dt
        if sim_ego_speed < 0:
            sim_ego_speed = 0
        sim_ego_pos += sim_ego_speed * dt
        
        # Format output
        dist_err_str = f"{dist_error:.2f}" if dist_error is not None else ''
        dist_str = f"{current_dist:.2f}" if current_dist is not None else ''
        
        results.append({
            'time': f"{time:.1f}",
            'ego_speed': f"{sim_ego_speed:.2f}",
            'acceleration_cmd': f"{accel_cmd:.2f}",
            'mode': mode,
            'distance_error': dist_err_str,
            'distance': dist_str,
            'ttc': ttc
        })

    # Write results
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

if __name__ == '__main__':
    run_simulation()

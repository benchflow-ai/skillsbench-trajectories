import yaml
import csv
import math
from acc_system import AdaptiveCruiseControl

def run_simulation(params_file, tuning_file, sensor_file, output_file):
    with open(params_file, 'r') as f:
        params = yaml.safe_load(f)
    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)
    
    acc = AdaptiveCruiseControl(params)
    acc.set_pids(tuning['pid_speed'], tuning['pid_distance'])
    
    dt = params['simulation']['dt']
    
    sensor_data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_data.append(row)
    
    ego_speed = 0.0
    ego_pos = -200.0  # Initial offset to avoid passing lead vehicle too early
    sensor_ego_pos = 0.0
    
    results = []
    
    for i in range(len(sensor_data)):
        row = sensor_data[i]
        t = float(row['time'])
        
        # Lead vehicle info from sensor data
        v_lead_str = row['lead_speed']
        d_sensor_str = row['distance']
        v_ego_sensor = float(row['ego_speed'])
        
        if v_lead_str and d_sensor_str:
            v_lead = float(v_lead_str)
            d_sensor = float(d_sensor_str)
            # Position of lead vehicle: current sensor ego pos + sensor distance
            p_lead = sensor_ego_pos + d_sensor
            d_sim = p_lead - ego_pos
            if d_sim < 0:
                d_sim = None
                v_lead = None
        else:
            v_lead = None
            d_sim = None
            p_lead = None

        # ACC compute
        accel_cmd, mode, d_error = acc.compute(ego_speed, v_lead, d_sim, dt)
        
        # Calculate TTC for logging
        ttc = None
        if v_lead is not None and d_sim is not None:
            rel_speed = ego_speed - v_lead
            if rel_speed > 0:
                ttc = d_sim / rel_speed
            else:
                ttc = float('inf')
        
        # Log results
        results.append({
            'time': f"{t:.1f}",
            'ego_speed': f"{ego_speed:.1f}",
            'acceleration_cmd': f"{accel_cmd:.1f}",
            'mode': mode,
            'distance_error': f"{d_error:.1f}" if d_error is not None else "",
            'distance': f"{d_sim:.1f}" if d_sim is not None else "",
            'ttc': f"{ttc:.1f}" if ttc is not None and ttc != float('inf') else ("inf" if ttc == float('inf') else "")
        })
        
        # Update simulation state
        # v_new = v_old + a * dt
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed) # Speed cannot be negative
        ego_pos += ego_speed * dt # Using new speed for simplicity or average
        
        # Update sensor ego position to track lead vehicle relative to sensor data
        sensor_ego_pos += v_ego_sensor * dt

    # Write results
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

if __name__ == "__main__":
    run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv', 'simulation_results.csv')

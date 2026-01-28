import pandas as pd
import yaml
import csv
import math
from acc_system import AdaptiveCruiseControl

def run_simulation():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
        config['pid_speed'].update(tuning['pid_speed'])
        config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass
    
    sensor_data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    ego_speed = 0.0
    results = []
    
    for i in range(len(sensor_data)):
        row = sensor_data.iloc[i]
        time = row['time']
        lead_speed = row['lead_speed']
        distance = row['distance']
        
        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        ttc = None
        try:
            l_speed = float(lead_speed)
            dist = float(distance)
            rel_speed = ego_speed - l_speed
            if rel_speed > 0:
                ttc = dist / rel_speed
            else:
                ttc = float('inf')
        except (TypeError, ValueError):
            pass

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': distance,
            'ttc': ttc
        })
        
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)

    keys = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for res in results:
            formatted_res = {}
            for k in keys:
                v = res[k]
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    formatted_res[k] = ''
                elif k == 'ttc' and v == float('inf'):
                    formatted_res[k] = 'inf'
                elif isinstance(v, float):
                    formatted_res[k] = round(v, 4)
                else:
                    formatted_res[k] = v
            writer.writerow(formatted_res)

if __name__ == "__main__":
    run_simulation()

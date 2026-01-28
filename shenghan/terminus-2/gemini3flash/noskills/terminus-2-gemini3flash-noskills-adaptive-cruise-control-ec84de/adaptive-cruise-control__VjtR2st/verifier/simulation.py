import pandas as pd
import yaml
import csv
from acc_system import AdaptiveCruiseControl

def run_simulation():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            if tuning:
                config['pid_speed'].update(tuning['pid_speed'])
                config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass

    acc = AdaptiveCruiseControl(config)
    sensor_data = pd.read_csv('sensor_data.csv')
    
    results = []
    ego_speed = 0.0
    current_distance = None
    dt = config['simulation']['dt']
    
    for i, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        if pd.isna(lead_speed):
            lead_speed = None
            current_distance = None
        else:
            if current_distance is None:
                current_distance = csv_distance
            else:
                current_distance += (lead_speed - ego_speed) * dt
        
        accel, mode, dist_error = acc.compute(ego_speed, lead_speed, current_distance, dt)
        
        ttc = None
        if mode != 'cruise' and lead_speed is not None and ego_speed > lead_speed:
            ttc = current_distance / (ego_speed - lead_speed)
            
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else '',
            'distance': round(current_distance, 2) if current_distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        })
        
        ego_speed += accel * dt
        ego_speed = max(0, ego_speed)

    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])
        writer.writeheader()
        for res in results:
            writer.writerow(res)

if __name__ == '__main__':
    run_simulation()

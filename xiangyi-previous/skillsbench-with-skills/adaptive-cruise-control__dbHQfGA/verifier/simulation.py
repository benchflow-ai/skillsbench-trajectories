import pandas as pd
import yaml
import numpy as np
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

    results = []
    ego_speed = 0.0

    for i, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        distance = row['distance']

        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        ttc = None
        if distance is not None and not np.isnan(distance) and lead_speed is not None and not np.isnan(lead_speed):
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed

        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_err, 2) if dist_err is not None else '',
            'distance': round(distance, 2) if not np.isnan(distance) else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        })

        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)

    df_results = pd.DataFrame(results)
    df_results.to_csv('simulation_results.csv', index=False)
    print("Simulation complete. Results saved to simulation_results.csv")

if __name__ == "__main__":
    run_simulation()

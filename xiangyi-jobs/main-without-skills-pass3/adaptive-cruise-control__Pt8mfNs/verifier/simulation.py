import math
import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    # override PID gains from tuning_results.yaml if present
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
        cfg['pid_speed'] = tuning['pid_speed']
        cfg['pid_distance'] = tuning['pid_distance']
    except FileNotFoundError:
        pass
    return cfg


def run_simulation():
    cfg = load_config()
    dt = cfg['simulation']['dt']
    max_acc = cfg['vehicle']['max_acceleration']
    max_dec = cfg['vehicle']['max_deceleration']

    acc = AdaptiveCruiseControl(cfg)

    data = pd.read_csv('sensor_data.csv')

    ego_speed = 0.0
    distance = None

    results = []

    for idx, row in data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        lead_distance = row['distance']

        if math.isnan(lead_speed) or math.isnan(lead_distance):
            lead_speed_val = None
            lead_distance_val = None
            distance = None
        else:
            lead_speed_val = float(lead_speed)
            if distance is None:
                distance = float(lead_distance)
            lead_distance_val = distance

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed_val, lead_distance_val, dt)

        # clamp acceleration
        accel_cmd = max(max_dec, min(max_acc, accel_cmd))

        # update ego speed
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # update distance if lead present
        if lead_speed_val is not None and distance is not None:
            distance = max(0.0, distance + (lead_speed_val - ego_speed) * dt)

        # compute ttc for logging
        if lead_speed_val is None or distance is None:
            ttc = None
        else:
            rel_speed = ego_speed - lead_speed_val
            if rel_speed > 1e-3:
                ttc = distance / rel_speed
            else:
                ttc = math.inf

        results.append({
            'time': round(time, 1),
            'ego_speed': round(ego_speed, 3),
            'acceleration_cmd': round(accel_cmd, 3),
            'mode': mode,
            'distance_error': None if distance_error is None else round(distance_error, 3),
            'distance': None if distance is None else round(distance, 3),
            'ttc': None if ttc is None or math.isinf(ttc) else round(ttc, 3)
        })

    out_df = pd.DataFrame(results)
    out_df.to_csv('simulation_results.csv', index=False)


if __name__ == '__main__':
    run_simulation()

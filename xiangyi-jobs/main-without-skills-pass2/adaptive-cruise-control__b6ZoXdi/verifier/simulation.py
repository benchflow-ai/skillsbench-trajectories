import math
import yaml
import pandas as pd

from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def main():
    config = load_yaml('vehicle_params.yaml')
    gains = load_yaml('tuning_results.yaml')

    acc = AdaptiveCruiseControl(config)
    acc.speed_pid = PIDController(gains['pid_speed']['kp'], gains['pid_speed']['ki'], gains['pid_speed']['kd'])
    acc.distance_pid = PIDController(gains['pid_distance']['kp'], gains['pid_distance']['ki'], gains['pid_distance']['kd'])

    dt = config['simulation']['dt']
    max_acc = config['vehicle']['max_acceleration']
    max_dec = config['vehicle']['max_deceleration']

    data = pd.read_csv('sensor_data.csv')

    ego_speed = 0.0
    results = []

    for _, row in data.iterrows():
        time = float(row['time'])
        lead_speed = row['lead_speed']
        lead_distance_meas = row['distance']

        lead_present = False
        if not (isinstance(lead_speed, float) and math.isnan(lead_speed)) and not (isinstance(lead_distance_meas, float) and math.isnan(lead_distance_meas)):
            lead_present = True

        distance = float(lead_distance_meas) if lead_present else None

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed if lead_present else None, distance, dt)

        # clamp
        accel_cmd = min(max_acc, max(max_dec, accel_cmd))
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        ttc = None
        if lead_present and distance is not None:
            relative_speed = ego_speed - float(lead_speed)
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        results.append({
            'time': round(time, 1),
            'ego_speed': round(ego_speed, 3),
            'acceleration_cmd': round(accel_cmd, 3),
            'mode': mode,
            'distance_error': None if distance_error is None else round(distance_error, 3),
            'distance': None if distance is None else round(distance, 3),
            'ttc': None if ttc is None or math.isinf(ttc) else round(ttc, 3)
        })

    df = pd.DataFrame(results)
    df.to_csv('simulation_results.csv', index=False, na_rep='')


if __name__ == '__main__':
    main()

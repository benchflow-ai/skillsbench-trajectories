import pandas as pd
import yaml
import math

from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def main():
    config = load_yaml('vehicle_params.yaml')
    dt = config['simulation']['dt']

    # Load tuning gains if available
    try:
        tuning = load_yaml('tuning_results.yaml')
    except FileNotFoundError:
        tuning = {}

    pid_speed_cfg = tuning.get('pid_speed', config.get('pid_speed', {}))
    pid_distance_cfg = tuning.get('pid_distance', config.get('pid_distance', {}))

    # Initialize PID controllers
    speed_pid = PIDController(pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd'],
                              output_min=config['vehicle']['max_deceleration'],
                              output_max=config['vehicle']['max_acceleration'])
    distance_pid = PIDController(pid_distance_cfg['kp'], pid_distance_cfg['ki'], pid_distance_cfg['kd'],
                                 output_min=-10.0, output_max=10.0)

    acc = AdaptiveCruiseControl(config, pid_speed=speed_pid, pid_distance=distance_pid)

    df = pd.read_csv('sensor_data.csv')

    results = []
    ego_speed = float(df.loc[0, 'ego_speed']) if not math.isnan(df.loc[0, 'ego_speed']) else 0.0
    distance = None

    for _, row in df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        lead_distance_input = row['distance']
        lead_present = not pd.isna(lead_speed)

        if not lead_present:
            distance = None
            accel_cmd, mode, distance_error = acc.compute(ego_speed, None, None, dt)
            ttc = None
        else:
            # initialize distance when lead appears
            if distance is None:
                distance = lead_distance_input if not pd.isna(lead_distance_input) else None
            else:
                # update distance based on relative speed
                distance = distance - (ego_speed - lead_speed) * dt
                if distance is not None:
                    distance = max(distance, 0.0)
            accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
            ttc = None
            if distance is not None:
                rel_speed = ego_speed - lead_speed
                if rel_speed > 0:
                    ttc = distance / rel_speed

        results.append({
            'time': round(time, 1),
            'ego_speed': round(ego_speed, 3),
            'acceleration_cmd': round(accel_cmd, 3),
            'mode': mode,
            'distance_error': None if distance_error is None else round(distance_error, 3),
            'distance': None if distance is None else round(distance, 3),
            'ttc': None if ttc is None else round(ttc, 3)
        })

        # update ego speed
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

    out_df = pd.DataFrame(results, columns=['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])
    out_df.to_csv('simulation_results.csv', index=False)


if __name__ == '__main__':
    main()

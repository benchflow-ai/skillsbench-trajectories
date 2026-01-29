"""Debug script to check simulation behavior."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    with open('/root/vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_tuning_results():
    with open('/root/tuning_results.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data():
    with open('/root/sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = []
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'].strip() else None,
                'distance': float(row['distance']) if row['distance'].strip() else None
            })
        return data


# Load configs
vehicle_config = load_config()
tuning = load_tuning_results()
vehicle_config['pid_speed'] = tuning['pid_speed']
vehicle_config['pid_distance'] = tuning['pid_distance']

acc = AdaptiveCruiseControl(vehicle_config)
dt = vehicle_config['simulation']['dt']

sensor_data = load_sensor_data()

# Simulate first 50 timesteps
ego_speed = 0.0

print("Time\tEgo Spd\tAcc Cmd\tMode")
for i, row in enumerate(sensor_data[:50]):
    time = row['time']
    lead_speed = row['lead_speed']
    distance = row['distance']

    acc_cmd, mode, dist_err = acc.compute(
        ego_speed=ego_speed,
        lead_speed=lead_speed,
        distance=distance,
        dt=dt
    )

    ego_speed += acc_cmd * dt
    ego_speed = max(0.0, ego_speed)

    print(f"{time:.1f}\t{ego_speed:.2f}\t{acc_cmd:.2f}\t{mode}")

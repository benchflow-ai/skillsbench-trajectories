"""Debug tuning to understand speed controller behavior."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(filepath: str) -> dict:
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> list:
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def run_simulation(acc: AdaptiveCruiseControl, sensor_data: list, dt: float = 0.1) -> list:
    ego_speed = 0.0
    distance = None
    prev_had_lead = False
    results = []

    for sensor in sensor_data:
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        if lead_speed is not None and sensor_distance is not None:
            if not prev_had_lead:
                distance = sensor_distance
            else:
                distance += (lead_speed - ego_speed) * dt
                distance = max(0.0, distance)
            prev_had_lead = True
        else:
            distance = None
            prev_had_lead = False

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance,
        })

        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

    return results


def main():
    vehicle_config = load_config('vehicle_params.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')

    # Test with specific gains
    acc = AdaptiveCruiseControl(vehicle_config)
    acc.set_speed_controller(kp=1.0, ki=0.1, kd=0.5)
    acc.set_distance_controller(kp=0.5, ki=0.05, kd=0.2)

    results = run_simulation(acc, sensor_data)

    # Print first 120 entries (0-12 seconds)
    print("Initial cruise phase:")
    print("Time\tEgo Speed\tAccel Cmd\tMode")
    for r in results[:120]:
        print(f"{r['time']:.1f}\t{r['ego_speed']:.2f}\t\t{r['acceleration_cmd']:.2f}\t\t{r['mode']}")

    print("\n\nTransition to follow (t=28-35):")
    for r in results[280:350]:
        print(f"{r['time']:.1f}\t{r['ego_speed']:.2f}\t\t{r['acceleration_cmd']:.2f}\t\t{r['mode']}\t{r['distance']}")


if __name__ == '__main__':
    main()

import yaml
import csv
from acc_system import AdaptiveCruiseControl


def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_tuning_results():
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            return tuning
    except FileNotFoundError:
        return None


def load_sensor_data():
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def parse_value(value):
    if value == '' or value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def run_simulation():
    config = load_config()

    tuning = load_tuning_results()
    if tuning:
        config['pid_speed'] = tuning['pid_speed']
        config['pid_distance'] = tuning['pid_distance']

    acc_system = AdaptiveCruiseControl(config)

    sensor_data = load_sensor_data()

    results = []

    for row in sensor_data:
        time = float(row['time'])
        ego_speed = float(row['ego_speed'])
        lead_speed = parse_value(row['lead_speed'])
        distance = parse_value(row['distance'])

        dt = 0.1

        acceleration_cmd, mode, distance_error = acc_system.compute(
            ego_speed, lead_speed, distance, dt
        )

        if lead_speed is not None and distance is not None:
            ttc = distance / (ego_speed - lead_speed) if ego_speed > lead_speed else float('inf')
        else:
            ttc = None

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc != float('inf') else ''
        })

    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Simulation completed. Results saved to simulation_results.csv")
    print(f"Total simulation time: {results[-1]['time']}s")
    print(f"Total data points: {len(results)}")


if __name__ == '__main__':
    run_simulation()

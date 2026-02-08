"""ACC simulation runner.

Reads PID gains from tuning_results.yaml, vehicle config from vehicle_params.yaml,
and lead vehicle data from sensor_data.csv. Outputs simulation_results.csv.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(path):
    """Load sensor data CSV and return list of dicts with parsed values."""
    rows = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
            }
            # lead_speed and distance may be empty (no lead vehicle)
            if row['lead_speed'].strip():
                entry['lead_speed'] = float(row['lead_speed'])
            else:
                entry['lead_speed'] = None
            if row['distance'].strip():
                entry['distance'] = float(row['distance'])
            else:
                entry['distance'] = None
            rows.append(entry)
    return rows


def run_simulation():
    # Load configuration
    vehicle_config = load_yaml('vehicle_params.yaml')
    tuning = load_yaml('tuning_results.yaml')

    # Merge tuned PID gains into config
    config = {
        'vehicle': vehicle_config['vehicle'],
        'acc_settings': vehicle_config['acc_settings'],
        'pid_speed': tuning['pid_speed'],
        'pid_distance': tuning['pid_distance'],
    }

    dt = vehicle_config['simulation']['dt']

    # Load sensor data for lead vehicle information
    sensor_data = load_sensor_data('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation state
    ego_speed = 0.0
    # We track distance ourselves; initialize from first sensor row that has it
    distance = None

    results = []

    for i, sensor_row in enumerate(sensor_data):
        t = sensor_row['time']
        lead_speed = sensor_row['lead_speed']
        sensor_distance = sensor_row['distance']

        # On the first timestep with lead vehicle data, initialize distance
        if lead_speed is not None and sensor_distance is not None:
            if distance is None:
                distance = sensor_distance
        elif lead_speed is None:
            distance = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record current state
        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(distance_error, 2) if distance_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else '',
        })

        # Update ego speed (kinematics)
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot be negative

        # Update distance if following a lead vehicle
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            distance = distance - relative_speed * dt
            distance = max(0.0, distance)

    # Write results
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Simulation complete: {len(results)} rows written to simulation_results.csv")
    return results


if __name__ == '__main__':
    run_simulation()

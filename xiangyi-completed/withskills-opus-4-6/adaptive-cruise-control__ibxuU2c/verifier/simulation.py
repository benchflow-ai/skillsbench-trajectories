"""ACC simulation runner.

Reads PID gains from tuning_results.yaml, vehicle config from vehicle_params.yaml,
and lead vehicle data from sensor_data.csv. Runs a 150s simulation and outputs
simulation_results.csv.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and merge tuned PID gains."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Override default PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data():
    """Load lead vehicle data from sensor_data.csv.

    Returns:
        List of dicts with time, lead_speed, distance (initial sensor reading).
    """
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = round(float(row['time']), 1)
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            init_distance = float(row['distance']) if row['distance'] else None
            data.append({'time': t, 'lead_speed': lead_speed, 'init_distance': init_distance})
    return data


def run_simulation():
    """Run the ACC simulation for 150 seconds."""
    config = load_config()
    acc = AdaptiveCruiseControl(config)
    sensor_data = load_sensor_data()

    dt = config['simulation']['dt']
    ego_speed = 0.0
    distance = None  # Dynamic distance tracking
    results = []

    for step in range(1501):
        t = round(step * dt, 1)
        sensor = sensor_data[step]
        lead_speed = sensor['lead_speed']

        # Manage distance state
        if lead_speed is None:
            # No lead vehicle
            distance = None
        elif distance is None:
            # Lead vehicle just appeared - use sensor initial distance
            distance = sensor['init_distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.01:
                ttc = distance / rel_speed

        results.append({
            'time': f'{t:.1f}',
            'ego_speed': f'{round(ego_speed, 4)}',
            'acceleration_cmd': f'{round(accel_cmd, 4)}',
            'mode': mode,
            'distance_error': f'{round(distance_error, 4)}' if distance_error is not None else '',
            'distance': f'{round(distance, 4)}' if distance is not None else '',
            'ttc': f'{round(ttc, 4)}' if ttc is not None else '',
        })

        # Update ego speed for next step
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Update distance dynamically: distance changes by (lead_speed - ego_speed) * dt
        if distance is not None and lead_speed is not None:
            distance = distance + (lead_speed - ego_speed) * dt
            distance = max(0.0, distance)

    # Write results
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f'Simulation complete. Wrote {len(results)} rows to simulation_results.csv')
    return results


if __name__ == '__main__':
    run_simulation()

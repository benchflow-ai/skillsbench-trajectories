"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(params_file: str, tuning_file: str) -> dict:
    """Load vehicle parameters and merge with tuned PID gains.

    Args:
        params_file: Path to vehicle_params.yaml
        tuning_file: Path to tuning_results.yaml

    Returns:
        Merged configuration dictionary
    """
    with open(params_file, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(sensor_file: str) -> list:
    """Load sensor data from CSV file.

    Args:
        sensor_file: Path to sensor_data.csv

    Returns:
        List of dicts with time, lead_speed, distance
    """
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def run_simulation(config: dict, sensor_data: list, output_file: str):
    """Run ACC simulation and save results.

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor readings
        output_file: Path to output CSV file
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Initial state
    ego_speed = 0.0
    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Compute acceleration command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Store result
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego speed for next timestep (simple Euler integration)
        ego_speed = ego_speed + accel_cmd * dt

        # Ensure speed doesn't go negative
        ego_speed = max(0.0, ego_speed)

    # Write results to CSV
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else ''
            })

    return results


def main():
    """Main entry point."""
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')
    results = run_simulation(config, sensor_data, 'simulation_results.csv')
    print(f"Simulation complete. {len(results)} timesteps written to simulation_results.csv")


if __name__ == '__main__':
    main()

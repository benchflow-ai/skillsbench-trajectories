"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import yaml
from typing import Optional
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file.

    Args:
        filepath: Path to sensor_data.csv

    Returns:
        List of dictionaries with time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """Load configuration from YAML files.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml

    Returns:
        Combined configuration dictionary
    """
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def run_simulation(
    config: dict,
    sensor_data: list,
    dt: float = 0.1
) -> list:
    """Run ACC simulation.

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor data entries
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)
    results = []

    # Initial state
    ego_speed = 0.0

    for entry in sensor_data:
        time = entry['time']
        lead_speed = entry['lead_speed']
        distance = entry['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record result
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)

        # Update ego speed for next iteration
        ego_speed = ego_speed + accel_cmd * dt

        # Clamp speed to non-negative
        ego_speed = max(0.0, ego_speed)

    return results


def save_results(results: list, filepath: str):
    """Save simulation results to CSV.

    Args:
        results: List of result dictionaries
        filepath: Output file path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results:
            # Format values
            formatted = {
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else ''
            }
            writer.writerow(formatted)


def main():
    """Run the ACC simulation."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    dt = config['simulation']['dt']
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total time steps: {len(results)}")


if __name__ == '__main__':
    main()

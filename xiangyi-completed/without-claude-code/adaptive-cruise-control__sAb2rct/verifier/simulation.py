"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import yaml
from typing import Optional
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath: str) -> list:
    """
    Load sensor data from CSV file.

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
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else None,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def load_config(params_path: str, tuning_path: str) -> dict:
    """
    Load vehicle parameters and merge with tuned PID gains.

    Args:
        params_path: Path to vehicle_params.yaml
        tuning_path: Path to tuning_results.yaml

    Returns:
        Merged configuration dictionary
    """
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def calculate_ttc(ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
    """
    Calculate Time-To-Collision.

    Args:
        ego_speed: Ego vehicle speed in m/s
        lead_speed: Lead vehicle speed in m/s
        distance: Distance to lead vehicle in meters

    Returns:
        TTC in seconds, or None if not approaching
    """
    closing_speed = ego_speed - lead_speed
    if closing_speed <= 0:
        return None
    return distance / closing_speed


def run_simulation(config: dict, sensor_data: list) -> list:
    """
    Run the ACC simulation.

    Args:
        config: Configuration dictionary with ACC settings and PID gains
        sensor_data: List of sensor data entries from CSV

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    results = []
    ego_speed = 0.0  # Start from rest

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            ttc = calculate_ttc(ego_speed, lead_speed, distance)

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

        # Update ego speed for next timestep
        ego_speed = ego_speed + accel_cmd * dt

        # Clamp speed to non-negative
        ego_speed = max(0.0, ego_speed)

    return results


def write_results(results: list, filepath: str):
    """
    Write simulation results to CSV.

    Args:
        results: List of simulation result dictionaries
        filepath: Output CSV filepath
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {
                'time': result['time'],
                'ego_speed': round(result['ego_speed'], 2) if result['ego_speed'] is not None else '',
                'acceleration_cmd': round(result['acceleration_cmd'], 2),
                'mode': result['mode'],
                'distance_error': round(result['distance_error'], 2) if result['distance_error'] is not None else '',
                'distance': round(result['distance'], 2) if result['distance'] is not None else '',
                'ttc': round(result['ttc'], 2) if result['ttc'] is not None else ''
            }
            writer.writerow(row)


def main():
    """Main entry point for simulation."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data)

    # Write results
    write_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results written to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")


if __name__ == '__main__':
    main()

"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import yaml
import math


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """Load vehicle configuration and tuned PID parameters.

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


def load_sensor_data(sensor_data_path: str) -> list:
    """Load sensor data from CSV file.

    Args:
        sensor_data_path: Path to sensor_data.csv

    Returns:
        List of dictionaries with sensor readings
    """
    sensor_data = []
    with open(sensor_data_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            sensor_data.append(entry)
    return sensor_data


def run_simulation(config: dict, sensor_data: list, dt: float = 0.1) -> list:
    """Run the ACC simulation.

    Args:
        config: Configuration dictionary with vehicle and PID parameters
        sensor_data: List of sensor readings from CSV
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    from acc_system import AdaptiveCruiseControl

    acc = AdaptiveCruiseControl(config)

    # Initial conditions
    ego_speed = 0.0
    ego_position = 0.0

    # Get initial lead vehicle position from first distance reading
    # Find first entry with distance data to establish lead vehicle position
    lead_position = None
    for sensor in sensor_data:
        if sensor['distance'] is not None:
            # Lead vehicle initial position is ego position + initial distance
            # We need to track lead vehicle position separately
            break

    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Calculate current distance based on simulated ego position
        # If lead vehicle is present in sensor data, compute actual distance
        if lead_speed is not None and sensor_distance is not None:
            # Use sensor data to determine lead vehicle behavior
            # The distance in sensor_data represents reference scenario
            # We compute our own distance based on our simulated position

            # Initialize lead position tracking on first detection
            if lead_position is None:
                lead_position = ego_position + sensor_distance

            # Update lead position based on lead speed
            if i > 0:
                lead_position += lead_speed * dt

            # Compute actual distance
            distance = lead_position - ego_position
            distance = max(0.0, distance)  # Can't have negative distance
        else:
            distance = None
            lead_position = None  # Reset when lead vehicle disappears

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None and distance > 0:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = None  # Not closing
        else:
            ttc = None

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

        # Update vehicle state for next timestep
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Ensure speed doesn't go negative

        # Update ego position
        ego_position += ego_speed * dt

    return results


def save_results(results: list, output_path: str):
    """Save simulation results to CSV file.

    Args:
        results: List of result dictionaries
        output_path: Path to output CSV file
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results:
            # Format values
            formatted_row = {
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else ''
            }
            writer.writerow(formatted_row)


def main():
    """Main entry point for simulation."""
    # File paths
    vehicle_params_path = 'vehicle_params.yaml'
    tuning_results_path = 'tuning_results.yaml'
    sensor_data_path = 'sensor_data.csv'
    output_path = 'simulation_results.csv'

    # Load configuration with tuned PID gains
    config = load_config(vehicle_params_path, tuning_results_path)

    # Load sensor data
    sensor_data = load_sensor_data(sensor_data_path)

    # Get timestep from config
    dt = config['simulation']['dt']

    # Run simulation
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, output_path)

    print(f"Simulation complete. Results saved to {output_path}")
    print(f"Total timesteps: {len(results)}")


if __name__ == '__main__':
    main()

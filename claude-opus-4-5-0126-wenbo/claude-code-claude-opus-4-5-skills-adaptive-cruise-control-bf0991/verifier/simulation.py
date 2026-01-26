"""
Simulation script for Adaptive Cruise Control.

Reads PID gains from tuning_results.yaml and uses sensor_data.csv for lead vehicle data.
Outputs simulation_results.csv with exactly 1501 rows.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """
    Load configuration from vehicle_params.yaml and override PID gains from tuning_results.yaml.

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

    # Override PID gains from tuning results
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(sensor_data_path: str) -> list:
    """
    Load sensor data from CSV file.

    Args:
        sensor_data_path: Path to sensor_data.csv

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(sensor_data_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else None,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def run_simulation(
    config: dict,
    sensor_data: list,
    output_path: str
):
    """
    Run the ACC simulation and output results.

    Uses sensor_data for lead vehicle information (lead_speed, distance as initial reference).
    Simulates ego vehicle dynamics with ACC control.
    Distance is dynamically calculated based on vehicle positions.

    Args:
        config: Configuration dictionary with ACC and vehicle params
        sensor_data: List of sensor data entries
        output_path: Path to output CSV file
    """
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']

    # Initial state
    ego_speed = 0.0  # Start from ~0 m/s
    ego_position = 0.0  # Starting position

    # Initialize lead vehicle position based on first sensor reading with lead vehicle
    lead_position = None
    for sensor in sensor_data:
        if sensor['lead_speed'] is not None and sensor['distance'] is not None:
            # Calculate lead position when it first appears
            # At this point, we need to estimate where the lead vehicle will be
            lead_position = None  # Will be set when lead vehicle appears
            break

    # Results storage
    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']  # Reference distance from sensor

        # Calculate distance based on positions if lead vehicle present
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                # First time seeing lead vehicle - initialize lead position based on sensor distance
                lead_position = ego_position + sensor_distance

            distance = lead_position - ego_position
            # Ensure distance is non-negative
            distance = max(0.0, distance)
        else:
            distance = None
            lead_position = None  # Reset when no lead vehicle

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed=ego_speed,
            lead_speed=lead_speed,
            distance=distance,
            dt=dt
        )

        # Calculate TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None and distance > 0:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
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

        # Update ego vehicle state for next timestep (Euler integration)
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Clamp to non-negative
        ego_position = ego_position + ego_speed * dt

        # Update lead vehicle position if present
        if lead_speed is not None and lead_position is not None:
            lead_position = lead_position + lead_speed * dt

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            row = {
                'time': r['time'],
                'ego_speed': round(r['ego_speed'], 2) if r['ego_speed'] is not None else '',
                'acceleration_cmd': round(r['acceleration_cmd'], 2) if r['acceleration_cmd'] is not None else '',
                'mode': r['mode'],
                'distance_error': round(r['distance_error'], 2) if r['distance_error'] is not None else '',
                'distance': round(r['distance'], 2) if r['distance'] is not None else '',
                'ttc': round(r['ttc'], 2) if r['ttc'] is not None else ''
            }
            writer.writerow(row)

    print(f"Simulation completed. Results written to {output_path}")
    print(f"Total timesteps: {len(results)}")


def main():
    """Main entry point for the simulation."""
    # File paths
    vehicle_params_path = 'vehicle_params.yaml'
    tuning_results_path = 'tuning_results.yaml'
    sensor_data_path = 'sensor_data.csv'
    output_path = 'simulation_results.csv'

    # Load configuration and data
    config = load_config(vehicle_params_path, tuning_results_path)
    sensor_data = load_sensor_data(sensor_data_path)

    print(f"Loaded {len(sensor_data)} sensor data points")
    print(f"Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"PID Speed: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"PID Distance: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    # Run simulation
    run_simulation(config, sensor_data, output_path)


if __name__ == '__main__':
    main()

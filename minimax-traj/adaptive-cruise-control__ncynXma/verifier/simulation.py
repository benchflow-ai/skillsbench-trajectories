"""
Adaptive Cruise Control Simulation

This module runs the ACC simulation using sensor data and generates
results for analysis and performance evaluation.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle configuration from YAML files."""
    # Load vehicle parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains from tuning_results.yaml
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Merge tuning results into config
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(filename):
    """
    Load sensor data from CSV file.

    Args:
        filename (str): Path to sensor data CSV file

    Returns:
        list: List of dictionaries containing sensor data
    """
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse numeric values, handling empty strings
            parsed_row = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': row['lead_speed'].strip() if row['lead_speed'].strip() else None,
                'distance': float(row['distance']) if row['distance'].strip() else None
            }

            # Convert lead_speed to float if not None
            if parsed_row['lead_speed'] is not None:
                parsed_row['lead_speed'] = float(parsed_row['lead_speed'])

            data.append(parsed_row)

    return data


def run_simulation():
    """Run the ACC simulation and generate results."""
    # Load configuration and sensor data
    config = load_config()
    sensor_data = load_sensor_data('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize simulation state
    dt = config['simulation']['dt']
    results = []

    # Track current ego speed (starting from 0 m/s)
    current_ego_speed = 0.0

    for i, row in enumerate(sensor_data):
        time = row['time']
        sensor_ego_speed = row['ego_speed']
        lead_speed = row['lead_speed']
        distance = row['distance']

        # Compute acceleration command from ACC system
        acceleration_cmd, mode, distance_error = acc.compute(
            current_ego_speed, lead_speed, distance, dt
        )

        # Update ego speed based on acceleration
        current_ego_speed += acceleration_cmd * dt
        current_ego_speed = max(0.0, current_ego_speed)  # No reverse speed

        # Calculate TTC if lead vehicle is present
        ttc = ''
        if lead_speed is not None and distance is not None:
            relative_speed = current_ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = f"{distance / relative_speed:.2f}"

        # Prepare result row
        result_row = {
            'time': time,
            'ego_speed': f"{current_ego_speed:.1f}",
            'acceleration_cmd': f"{acceleration_cmd:.1f}",
            'mode': mode,
            'distance_error': f"{distance_error:.2f}" if distance_error is not None else '',
            'distance': f"{distance:.2f}" if distance is not None else '',
            'ttc': ttc
        }

        results.append(result_row)

    # Write results to CSV
    write_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results written to simulation_results.csv")
    print(f"Total time steps: {len(results)}")
    print(f"Final ego speed: {current_ego_speed:.2f} m/s")


def write_results(results, filename):
    """
    Write simulation results to CSV file.

    Args:
        results (list): List of result dictionaries
        filename (str): Output CSV filename
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == '__main__':
    run_simulation()

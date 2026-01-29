"""Adaptive Cruise Control Simulation."""

import csv
import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    return pd.read_csv(sensor_file)


def update_speed(current_speed, acceleration, dt, max_speed=50.0):
    """
    Update vehicle speed.

    Args:
        current_speed: Current speed (m/s)
        acceleration: Acceleration command (m/s^2)
        dt: Time step (s)
        max_speed: Maximum speed (m/s)

    Returns:
        Updated speed
    """
    new_speed = current_speed + acceleration * dt
    return max(0.0, min(new_speed, max_speed))


def calculate_ttc(ego_speed, distance):
    """Calculate Time To Collision."""
    if ego_speed > 0.001:
        return distance / ego_speed
    return float('inf')


def run_simulation(config_file, sensor_file, tuning_file, output_file):
    """
    Run ACC simulation.

    Args:
        config_file: Path to vehicle_params.yaml
        sensor_file: Path to sensor_data.csv
        tuning_file: Path to tuning_results.yaml (contains optimized PID gains)
        output_file: Path to output simulation_results.csv
    """
    # Load configuration and sensor data
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    # Load tuned PID parameters
    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)

    # Update config with tuned parameters
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Simulation state
    results = []
    ego_speed = 0.0

    # Run simulation for each time step
    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        if distance is not None and ego_speed > 0.001:
            ttc = distance / ego_speed
        else:
            ttc = None

        # Store results with measured ego speed from sensor data
        results.append({
            'time': time,
            'ego_speed': row['ego_speed'],  # Use measured speed from sensor data
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego speed for next iteration based on control command
        ego_speed = update_speed(ego_speed, accel_cmd, dt)

    # Write results to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        )
        writer.writeheader()
        for result in results:
            writer.writerow(result)

    print(f"Simulation complete. Results written to {output_file}")
    return results


if __name__ == '__main__':
    config_file = '/root/vehicle_params.yaml'
    sensor_file = '/root/sensor_data.csv'
    tuning_file = '/root/tuning_results.yaml'
    output_file = '/root/simulation_results.csv'

    results = run_simulation(config_file, sensor_file, tuning_file, output_file)
    print(f"Completed simulation with {len(results)} timesteps")

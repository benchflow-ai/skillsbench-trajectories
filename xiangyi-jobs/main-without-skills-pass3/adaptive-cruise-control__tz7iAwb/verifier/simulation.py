"""
Adaptive Cruise Control Simulation.

Runs a 150-second simulation of the ACC system using sensor data from real-world driving.
Loads PID gains from tuning_results.yaml and produces simulation results in CSV format.
"""

import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath):
    """
    Load sensor data from CSV file.

    Args:
        filepath (str): Path to sensor_data.csv

    Returns:
        list: List of dictionaries with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = row['lead_speed'].strip() if row['lead_speed'].strip() else None
            distance = row['distance'].strip() if row['distance'].strip() else None

            if lead_speed:
                lead_speed = float(lead_speed)
            if distance:
                distance = float(distance)

            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })

    return data


def load_config(vehicle_params_path, tuning_results_path):
    """
    Load configuration from YAML files.

    Args:
        vehicle_params_path (str): Path to vehicle_params.yaml
        tuning_results_path (str): Path to tuning_results.yaml

    Returns:
        dict: Merged configuration with vehicle, acc_settings, and PID gains
    """
    # Load vehicle and ACC settings
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Merge tuning results into config
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def simulate_dynamics(current_speed, accel_cmd, max_accel, max_decel, dt):
    """
    Simulate vehicle dynamics with acceleration command.

    Simple kinematic model: v_next = v_current + a * dt
    Acceleration is limited by vehicle constraints.

    Args:
        current_speed (float): Current vehicle speed (m/s)
        accel_cmd (float): Commanded acceleration (m/s^2)
        max_accel (float): Maximum acceleration (m/s^2)
        max_decel (float): Maximum deceleration (m/s^2)
        dt (float): Time step (s)

    Returns:
        float: New vehicle speed after time step
    """
    # Clamp acceleration command to vehicle limits
    accel = max(max_decel, min(max_accel, accel_cmd))

    # Update speed
    new_speed = current_speed + accel * dt

    # Ensure speed is non-negative
    new_speed = max(0.0, new_speed)

    return new_speed


def run_simulation(sensor_data, config, output_csv):
    """
    Run the ACC simulation over the provided sensor data.

    Args:
        sensor_data (list): List of sensor measurement dictionaries
        config (dict): Configuration dictionary
        output_csv (str): Output file path for simulation results
    """
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Simulation state
    results = []

    # Run simulation for each time step
    for measurement in sensor_data:
        time = measurement['time']
        measured_ego_speed = measurement['ego_speed']
        lead_speed = measurement['lead_speed']
        distance = measurement['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            measured_ego_speed, lead_speed, distance, dt
        )

        # Simulate vehicle dynamics
        ego_speed_next = simulate_dynamics(
            measured_ego_speed, accel_cmd, max_accel, max_decel, dt
        )

        # Compute TTC if lead vehicle is present
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = measured_ego_speed - lead_speed
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed

        # Store result
        result_row = {
            'time': time,
            'ego_speed': ego_speed_next,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        }
        results.append(result_row)

    # Write results to CSV
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Format numbers to appropriate precision
            row = {
                'time': f"{result['time']:.1f}",
                'ego_speed': f"{result['ego_speed']:.1f}",
                'acceleration_cmd': f"{result['acceleration_cmd']:.2f}",
                'mode': result['mode'],
                'distance_error': f"{result['distance_error']:.2f}" if result['distance_error'] != '' else '',
                'distance': f"{result['distance']:.2f}" if result['distance'] != '' else '',
                'ttc': f"{result['ttc']:.2f}" if result['ttc'] != '' else ''
            }
            writer.writerow(row)


def main():
    """Run the complete ACC simulation."""
    print("Initializing ACC Simulation...")

    # Load data and configuration
    sensor_data = load_sensor_data('/root/sensor_data.csv')
    config = load_config('/root/vehicle_params.yaml', '/root/tuning_results.yaml')

    print(f"Loaded {len(sensor_data)} sensor measurements")
    print(f"Simulation duration: {sensor_data[-1]['time']} seconds")
    print(f"Time step: {config['simulation']['dt']} seconds")

    print("\nRunning simulation...")
    run_simulation(sensor_data, config, '/root/simulation_results.csv')

    print("✓ Simulation complete: simulation_results.csv generated")


if __name__ == '__main__':
    main()

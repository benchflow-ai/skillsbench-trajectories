"""
ACC system simulation runner.

Reads vehicle configuration and sensor data, runs ACC simulation,
and generates results.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_file):
    """
    Load sensor data from CSV file.

    Returns:
        list: List of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None

            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def update_vehicle_state(ego_speed, accel_cmd, dt, max_accel, max_decel):
    """
    Update vehicle speed based on acceleration command.

    Args:
        ego_speed (float): Current speed (m/s)
        accel_cmd (float): Acceleration command (m/s^2)
        dt (float): Time step (s)
        max_accel (float): Maximum acceleration limit (m/s^2)
        max_decel (float): Maximum deceleration limit (m/s^2)

    Returns:
        float: New ego speed (m/s)
    """
    # Saturate acceleration command (should already be done in ACC, but double-check)
    accel_cmd = max(min(accel_cmd, max_accel), max_decel)

    # Update speed
    new_speed = ego_speed + accel_cmd * dt

    # Ensure non-negative speed
    new_speed = max(0.0, new_speed)

    return new_speed


def calculate_ttc(ego_speed, lead_speed, distance):
    """
    Calculate Time-To-Collision.

    Returns:
        float: TTC in seconds, or inf if not applicable
    """
    if distance is None or lead_speed is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed > 0 and distance > 0:
        return distance / relative_speed
    else:
        return None


def run_simulation(config_file, sensor_file, tuning_file):
    """
    Run ACC simulation.

    Args:
        config_file (str): Path to vehicle_params.yaml
        sensor_file (str): Path to sensor_data.csv
        tuning_file (str): Path to tuning_results.yaml (contains PID gains)

    Returns:
        list: List of result dicts for each timestep
    """
    # Load all data
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)
    tuning = load_config(tuning_file)

    # Update config with tuned PID parameters
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation state
    results = []
    ego_speed = 0.0
    dt = config['simulation']['dt']

    # Run simulation for each sensor data point
    for sensor_point in sensor_data:
        time = sensor_point['time']
        measured_ego_speed = sensor_point['ego_speed']
        lead_speed = sensor_point['lead_speed']
        distance = sensor_point['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update vehicle state
        ego_speed = update_vehicle_state(
            ego_speed,
            accel_cmd,
            dt,
            config['vehicle']['max_acceleration'],
            config['vehicle']['max_deceleration']
        )

        # Calculate TTC
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

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

    return results


def save_results(results, output_file):
    """Save simulation results to CSV file."""
    fieldnames = [
        'time',
        'ego_speed',
        'acceleration_cmd',
        'mode',
        'distance_error',
        'distance',
        'ttc'
    ]

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {
                'time': result['time'],
                'ego_speed': result['ego_speed'],
                'acceleration_cmd': result['acceleration_cmd'],
                'mode': result['mode'],
                'distance_error': result['distance_error'] if result['distance_error'] is not None else '',
                'distance': result['distance'] if result['distance'] is not None else '',
                'ttc': result['ttc'] if result['ttc'] is not None else ''
            }
            writer.writerow(row)


if __name__ == '__main__':
    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else '/root/vehicle_params.yaml'
    sensor_file = sys.argv[2] if len(sys.argv) > 2 else '/root/sensor_data.csv'
    tuning_file = sys.argv[3] if len(sys.argv) > 3 else '/root/tuning_results.yaml'
    output_file = sys.argv[4] if len(sys.argv) > 4 else '/root/simulation_results.csv'

    results = run_simulation(config_file, sensor_file, tuning_file)
    save_results(results, output_file)
    print(f"Simulation complete. Results saved to {output_file}")

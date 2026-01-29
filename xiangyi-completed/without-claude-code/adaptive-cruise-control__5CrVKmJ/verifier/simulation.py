"""
Adaptive Cruise Control simulation runner.
Loads sensor data, PID tuning parameters, and simulates vehicle control.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle configuration from vehicle_params.yaml."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_tuning_results():
    """Load tuned PID parameters from tuning_results.yaml."""
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    return tuning


def load_sensor_data():
    """
    Load sensor data from sensor_data.csv.

    Returns:
        list: List of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            # Handle empty lead_speed and distance
            lead_speed = float(row['lead_speed']) if row['lead_speed'].strip() else None
            distance = float(row['distance']) if row['distance'].strip() else None
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def simulate(config, tuning, sensor_data, duration=150.0, dt=0.1):
    """
    Run the ACC simulation.

    Args:
        config (dict): Vehicle configuration
        tuning (dict): Tuned PID parameters
        sensor_data (list): Sensor data from CSV
        duration (float): Simulation duration in seconds
        dt (float): Time step in seconds

    Returns:
        list: List of simulation result dicts
    """
    # Merge tuned parameters into config
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Create ACC system
    acc = AdaptiveCruiseControl(config)

    results = []
    num_steps = int(duration / dt) + 1

    for step in range(num_steps):
        if step < len(sensor_data):
            sensor = sensor_data[step]
        else:
            break

        time = sensor['time']
        measured_ego_speed = sensor['ego_speed']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Get control action
        accel_cmd, mode, distance_error = acc.compute(measured_ego_speed, lead_speed, distance, dt)

        # Calculate TTC if following
        if lead_speed is not None and distance is not None:
            relative_speed = measured_ego_speed - lead_speed
            if relative_speed > 0.1:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Record results
        result = {
            'time': time,
            'ego_speed': measured_ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)

    return results


def save_results(results, filename='simulation_results.csv'):
    """
    Save simulation results to CSV.

    Args:
        results (list): List of result dictionaries
        filename (str): Output filename
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Handle None values in output
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


def main():
    """Main simulation runner."""
    print("Loading configuration...")
    config = load_config()

    print("Loading tuning results...")
    tuning = load_tuning_results()

    print("Loading sensor data...")
    sensor_data = load_sensor_data()

    print(f"Running simulation for {len(sensor_data) * config['simulation']['dt']:.1f} seconds...")
    results = simulate(config, tuning, sensor_data, duration=150.0, dt=config['simulation']['dt'])

    print(f"Saving {len(results)} results to simulation_results.csv...")
    save_results(results)

    print("Simulation complete!")
    print(f"Total steps: {len(results)}")
    print(f"Simulation time: {results[-1]['time']:.1f}s")


if __name__ == '__main__':
    main()

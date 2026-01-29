"""Vehicle Simulation with Adaptive Cruise Control"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(yaml_file):
    """Load configuration from YAML file."""
    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_file):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def run_simulation(config, sensor_data, tuning_gains):
    """
    Run ACC simulation.

    Args:
        config (dict): Vehicle and ACC configuration
        sensor_data (list): Sensor data from CSV
        tuning_gains (dict): Tuned PID gains

    Returns:
        list: Simulation results
    """
    # Update config with tuned gains
    config['pid_speed'] = tuning_gains['pid_speed']
    config['pid_distance'] = tuning_gains['pid_distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']

    # Initialize state
    ego_speed = 0.0  # Starting from rest
    results = []

    for row in sensor_data:
        time = float(row['time'])
        lead_speed = row['lead_speed'] if row['lead_speed'] else None
        distance = row['distance'] if row['distance'] else None

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Update ego speed (simple integration)
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Prevent negative speed

        # Store results
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance if distance else '',
            'ttc': acc.compute_ttc(ego_speed, float(lead_speed) if lead_speed else None, float(distance) if distance else None) if lead_speed and distance else ''
        }
        results.append(result)

    return results


def save_results(results, output_file):
    """Save simulation results to CSV file."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)


def main():
    """Main simulation function."""
    # Load configuration
    config = load_config('vehicle_params.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Load tuned PID gains
    with open('tuning_results.yaml', 'r') as f:
        tuning_gains = yaml.safe_load(f)

    # Run simulation
    results = run_simulation(config, sensor_data, tuning_gains)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total simulation time: {results[-1]['time']:.1f} seconds")
    print(f"Final speed: {results[-1]['ego_speed']:.2f} m/s")


if __name__ == '__main__':
    main()

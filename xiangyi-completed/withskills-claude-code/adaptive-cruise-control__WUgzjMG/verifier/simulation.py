"""ACC simulation runner that loads sensor data and simulates the system."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, 'r') as f:
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


def simulate_acc(config, sensor_data):
    """
    Run ACC simulation using sensor data.

    Args:
        config (dict): Configuration dictionary
        sensor_data (list): List of sensor data points

    Returns:
        list: Simulation results with all computed values
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    results = []

    ego_speed = 0.0
    current_accel = 0.0

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Update ego speed using simplified dynamics
        current_accel = accel_cmd
        ego_speed += current_accel * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot be negative

        # Calculate TTC if lead vehicle present
        if distance is not None and lead_speed is not None:
            speed_diff = ego_speed - lead_speed
            if speed_diff > 0.1:
                ttc = distance / speed_diff
            else:
                ttc = None
        else:
            ttc = None

        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': current_accel,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)

    return results


def save_results(results, output_file):
    """Save simulation results to CSV file."""
    with open(output_file, 'w', newline='') as f:
        fieldnames = [
            'time', 'ego_speed', 'acceleration_cmd', 'mode',
            'distance_error', 'distance', 'ttc'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {}
            for field in fieldnames:
                value = result.get(field)
                if value is None:
                    row[field] = ''
                else:
                    row[field] = value
            writer.writerow(row)


def main():
    """Main simulation runner."""
    # Load configuration and sensor data
    config = load_config('vehicle_params.yaml')

    # Load tuned PID parameters from tuning_results.yaml
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning_results = yaml.safe_load(f)
        config['pid_speed'] = tuning_results['pid_speed']
        config['pid_distance'] = tuning_results['pid_distance']
        print("Loaded PID gains from tuning_results.yaml")
    except FileNotFoundError:
        print("tuning_results.yaml not found, using defaults from vehicle_params.yaml")

    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    print("Running ACC simulation...")
    results = simulate_acc(config, sensor_data)

    # Save results
    save_results(results, 'simulation_results.csv')
    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total simulation time: {results[-1]['time']:.1f} seconds")
    print(f"Final ego speed: {results[-1]['ego_speed']:.2f} m/s")

    return results


if __name__ == '__main__':
    main()

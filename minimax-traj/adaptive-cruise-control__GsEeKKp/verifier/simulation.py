"""Vehicle simulation with Adaptive Cruise Control system."""

import yaml
import csv
import os
from acc_system import AdaptiveCruiseControl


def load_config(config_path='vehicle_params.yaml'):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_tuning_results(tuning_path='tuning_results.yaml'):
    """Load tuned PID parameters from YAML file."""
    if not os.path.exists(tuning_path):
        # If tuning results don't exist, use defaults from vehicle_params.yaml
        config = load_config()
        return {
            'pid_speed': config.get('pid_speed', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0}),
            'pid_distance': config.get('pid_distance', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})
        }

    with open(tuning_path, 'r') as f:
        tuning_results = yaml.safe_load(f)
    return tuning_results


def load_sensor_data(csv_path='sensor_data.csv'):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse values, handling empty strings
            time = float(row['time'])
            ego_speed = float(row['ego_speed']) if row['ego_speed'] else 0.0
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else 0.0
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def run_simulation(output_path='simulation_results.csv'):
    """Run the ACC simulation."""
    # Load configuration
    config = load_config()

    # Load tuned PID parameters
    tuning_results = load_tuning_results()
    config['pid_speed'] = tuning_results['pid_speed']
    config['pid_distance'] = tuning_results['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data()

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_acceleration = config['vehicle']['max_acceleration']
    max_deceleration = config['vehicle']['max_deceleration']
    mass = config['vehicle']['mass']

    # Initialize simulation state
    current_speed = 0.0
    results = []

    print("Running ACC simulation...")
    print(f"Duration: {len(sensor_data) * dt:.1f} seconds")
    print(f"Timestep: {dt} seconds")

    # Run simulation for each timestep
    for i, data_point in enumerate(sensor_data):
        time = data_point['time']
        lead_speed = data_point['lead_speed']
        distance = data_point['distance']

        # Compute ACC control command
        acceleration_cmd, mode, distance_error = acc.compute(
            current_speed, lead_speed, distance, dt
        )

        # Apply acceleration limits
        acceleration_cmd = max(min(acceleration_cmd, max_acceleration), max_deceleration)

        # Update vehicle speed (simple dynamics)
        current_speed += acceleration_cmd * dt
        current_speed = max(0.0, current_speed)  # No negative speed

        # Calculate TTC
        ttc = float('inf')
        if lead_speed is not None and lead_speed > 0:
            relative_speed = current_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        # Store results
        result = {
            'time': time,
            'ego_speed': current_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error != 0.0 else '',
            'distance': distance if distance > 0 else '',
            'ttc': ttc if ttc != float('inf') else ''
        }
        results.append(result)

        # Print progress every 100 steps
        if i % 100 == 0:
            print(f"  Step {i}/{len(sensor_data)}: t={time:.1f}s, speed={current_speed:.2f} m/s, mode={mode}")

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)

    print(f"\nSimulation complete! Results saved to {output_path}")
    return results


if __name__ == '__main__':
    run_simulation()

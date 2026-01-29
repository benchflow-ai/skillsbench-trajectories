"""Vehicle simulation for Adaptive Cruise Control system."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl, load_config


def load_sensor_data(csv_path):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse lead_speed and distance, handle empty values
            lead_speed = row['lead_speed'].strip() if row['lead_speed'].strip() else None
            distance = row['distance'].strip() if row['distance'].strip() else None

            # Convert to appropriate types
            if lead_speed is not None:
                lead_speed = float(lead_speed)
            if distance is not None:
                distance = float(distance)

            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def load_tuned_pid_parameters(yaml_path):
    """Load tuned PID parameters from YAML file."""
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def update_ego_speed(current_speed, acceleration, dt):
    """Update ego vehicle speed based on acceleration."""
    new_speed = current_speed + acceleration * dt
    # Ensure speed doesn't go negative
    return max(0.0, new_speed)


def run_simulation():
    """Run the ACC simulation for 150 seconds."""
    # Load configuration
    vehicle_config = load_config('vehicle_params.yaml')
    tuning_config = load_tuned_pid_parameters('tuning_results.yaml')

    # Merge tuning results into vehicle config
    vehicle_config['pid_speed'] = tuning_config['pid_speed']
    vehicle_config['pid_distance'] = tuning_config['pid_distance']

    # Load sensor data (lead vehicle data)
    sensor_data = load_sensor_data('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(vehicle_config)

    # Simulation parameters
    dt = vehicle_config['simulation']['dt']

    # Initialize simulation state
    results = []
    ego_speed = 0.0  # Starting from rest
    ego_speed_actual = 0.0  # Track actual speed with acceleration limits

    # Run simulation for each time step
    for i, data_point in enumerate(sensor_data):
        time = data_point['time']
        lead_speed = data_point['lead_speed']
        distance = data_point['distance']

        # Use actual ego speed for control
        current_ego_speed = ego_speed_actual

        # Compute acceleration command from ACC
        acceleration_cmd, mode, distance_error = acc.compute(
            current_ego_speed, lead_speed, distance, dt
        )

        # Update actual ego speed (simulate vehicle dynamics with acceleration limits)
        # Note: acceleration_cmd already limited by ACC system
        new_ego_speed = update_ego_speed(current_ego_speed, acceleration_cmd, dt)

        # Calculate time-to-collision for reporting
        ttc = float('inf')
        if lead_speed is not None and distance is not None:
            relative_speed = current_ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        # Store results
        result_row = {
            'time': time,
            'ego_speed': new_ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc != float('inf') else ''
        }
        results.append(result_row)

        # Update speed for next iteration
        ego_speed_actual = new_ego_speed

    return results


def save_results_to_csv(results, output_path):
    """Save simulation results to CSV file."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    """Main simulation execution."""
    print("Starting ACC simulation...")

    # Run simulation
    results = run_simulation()

    # Save results
    output_path = 'simulation_results.csv'
    save_results_to_csv(results, output_path)

    print(f"Simulation complete! Results saved to {output_path}")
    print(f"Total simulation time steps: {len(results)}")


if __name__ == '__main__':
    main()

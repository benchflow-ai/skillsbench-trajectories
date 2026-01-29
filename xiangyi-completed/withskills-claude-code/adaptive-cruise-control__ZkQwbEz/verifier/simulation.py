"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath: str):
    """Load sensor data from CSV file."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def load_config(vehicle_params_path: str, tuning_results_path: str):
    """Load configuration from YAML files, using tuned PID gains."""
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    # Override with tuned PID gains
    with open(tuning_results_path, 'r') as f:
        tuned = yaml.safe_load(f)

    config['pid_speed'] = tuned['pid_speed']
    config['pid_distance'] = tuned['pid_distance']

    return config


def run_simulation(config: dict, sensor_data: list, dt: float = 0.1):
    """
    Run the ACC simulation.

    The simulation uses lead vehicle data (lead_speed) from sensor data
    and computes ego vehicle dynamics based on ACC control commands.
    Distance is computed from actual ego/lead positions.

    Args:
        config: Configuration dictionary with ACC settings and PID gains
        sensor_data: List of sensor data entries with lead vehicle info
        dt: Time step (seconds)

    Returns:
        List of simulation results for each time step
    """
    acc = AdaptiveCruiseControl(config)
    results = []

    # Initial conditions
    ego_speed = 0.0
    ego_position = 0.0

    # For lead vehicle tracking, we'll reconstruct position from speeds
    # Initial lead position is set when lead vehicle first appears
    lead_position = None
    prev_lead_speed = None

    for entry in sensor_data:
        time = entry['time']
        lead_speed = entry['lead_speed']
        sensor_distance = entry['distance']  # Distance from sensor for reference

        # Compute actual distance from positions
        if lead_speed is not None:
            if lead_position is None and sensor_distance is not None:
                # First time seeing lead vehicle - initialize position
                lead_position = ego_position + sensor_distance
                prev_lead_speed = lead_speed
            elif lead_position is not None:
                # Update lead position based on its speed
                if prev_lead_speed is not None:
                    lead_position = lead_position + prev_lead_speed * dt
                prev_lead_speed = lead_speed

            distance = lead_position - ego_position if lead_position is not None else None
        else:
            # No lead vehicle
            distance = None
            lead_position = None
            prev_lead_speed = None

        # Compute ACC command using computed distance
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego vehicle state for next iteration
        ego_position = ego_position + ego_speed * dt
        ego_speed = ego_speed + accel_cmd * dt
        # Ensure speed doesn't go negative
        ego_speed = max(0.0, ego_speed)

    return results


def save_results(results: list, filepath: str):
    """Save simulation results to CSV file."""
    with open(filepath, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            # Format numeric values
            formatted_row = {
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else ''
            }
            writer.writerow(formatted_row)


def main():
    """Main entry point for simulation."""
    # Load configuration with tuned PID gains
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    dt = config['simulation']['dt']
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total time steps: {len(results)}")


if __name__ == '__main__':
    main()

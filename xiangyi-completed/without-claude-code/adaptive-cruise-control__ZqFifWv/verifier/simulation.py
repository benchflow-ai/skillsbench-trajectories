"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """Load configuration from YAML files."""
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    # Override PID gains with tuned values
    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def run_simulation(config: dict, sensor_data: list, dt: float) -> list:
    """
    Run the ACC simulation.

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor readings with lead_speed and distance
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)

    # Initial conditions
    ego_speed = 0.0
    results = []

    for i, sensor in enumerate(sensor_data):
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Record result
        results.append({
            'time': sensor['time'],
            'ego_speed': round(ego_speed, 6),
            'acceleration_cmd': round(accel_cmd, 6),
            'mode': mode,
            'distance_error': round(distance_error, 6) if distance_error is not None else None,
            'distance': distance,
            'ttc': round(ttc, 6) if ttc is not None else None
        })

        # Update ego speed for next timestep
        ego_speed = ego_speed + accel_cmd * dt

        # Clamp speed to non-negative
        ego_speed = max(0.0, ego_speed)


    return results


def save_results(results: list, filepath: str):
    """Save simulation results to CSV file."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])

        for r in results:
            writer.writerow([
                r['time'],
                r['ego_speed'],
                r['acceleration_cmd'],
                r['mode'],
                '' if r['distance_error'] is None else r['distance_error'],
                '' if r['distance'] is None else r['distance'],
                '' if r['ttc'] is None else r['ttc']
            ])


def main():
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    dt = config['simulation']['dt']

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")


if __name__ == '__main__':
    main()

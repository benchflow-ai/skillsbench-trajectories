"""ACC Simulation - Runs the Adaptive Cruise Control simulation."""

import csv
import yaml
from typing import Optional
from acc_system import AdaptiveCruiseControl


def load_yaml(filepath: str) -> dict:
    """Load YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file.

    Returns list of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else None,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def run_simulation(
    vehicle_config: dict,
    tuning_config: dict,
    sensor_data: list,
    dt: float = 0.1
) -> list:
    """Run the ACC simulation.

    Args:
        vehicle_config: Vehicle parameters from vehicle_params.yaml
        tuning_config: Tuned PID gains from tuning_results.yaml
        sensor_data: Sensor data from sensor_data.csv
        dt: Time step in seconds

    Returns:
        List of result dicts for each timestep
    """
    # Merge tuned PID gains into config
    config = vehicle_config.copy()
    config['pid_speed'] = tuning_config['pid_speed']
    config['pid_distance'] = tuning_config['pid_distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize ego vehicle state
    ego_speed = 0.0  # Start from rest

    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']

        # Get lead vehicle data from sensor
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc,
        })

        # Update ego vehicle state using simple kinematics
        # v_new = v_old + a * dt
        ego_speed = ego_speed + accel_cmd * dt

        # Clamp speed to non-negative
        ego_speed = max(0.0, ego_speed)

    return results


def save_results(results: list, filepath: str):
    """Save simulation results to CSV file."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            # Format values
            formatted = {
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else '',
            }
            writer.writerow(formatted)


def main():
    """Main entry point for simulation."""
    # Load configurations
    vehicle_config = load_yaml('vehicle_params.yaml')
    tuning_config = load_yaml('tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Get timestep from config
    dt = vehicle_config.get('simulation', {}).get('dt', 0.1)

    # Run simulation
    results = run_simulation(vehicle_config, tuning_config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")


if __name__ == '__main__':
    main()

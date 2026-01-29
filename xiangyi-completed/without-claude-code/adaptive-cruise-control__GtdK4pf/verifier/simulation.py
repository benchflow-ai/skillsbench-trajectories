"""Vehicle simulation for Adaptive Cruise Control."""

import csv
from typing import Optional

import yaml

from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file.

    Args:
        filepath: Path to sensor_data.csv

    Returns:
        List of dicts with time, ego_speed, lead_speed, distance
    """
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


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """Load configuration from vehicle params and tuning results.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml

    Returns:
        Combined configuration dict
    """
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains from tuning results
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def calculate_ttc(ego_speed: float, lead_speed: Optional[float], distance: Optional[float]) -> Optional[float]:
    """Calculate Time To Collision.

    Args:
        ego_speed: Current ego vehicle speed in m/s
        lead_speed: Lead vehicle speed in m/s
        distance: Distance to lead vehicle in meters

    Returns:
        TTC in seconds, or None if not applicable
    """
    if lead_speed is None or distance is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None
    return distance / relative_speed


def run_simulation(
    config: dict,
    sensor_data: list,
    dt: float = 0.1
) -> list:
    """Run the ACC simulation.

    The simulation uses sensor data for lead vehicle information (speed) but
    simulates the ego vehicle dynamics based on ACC commands. Distance is
    calculated dynamically based on relative positions.

    Args:
        config: Configuration dict with vehicle and ACC parameters
        sensor_data: List of sensor data entries from CSV
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)

    # Initial conditions
    ego_speed = 0.0
    ego_position = 0.0

    # Lead vehicle tracking
    lead_position = None
    prev_lead_speed = None

    results = []

    for i, sensor_entry in enumerate(sensor_data):
        time = sensor_entry['time']
        lead_speed = sensor_entry['lead_speed']
        sensor_distance = sensor_entry['distance']

        # Handle lead vehicle position tracking
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                # Lead vehicle just appeared - initialize lead position
                lead_position = ego_position + sensor_distance
            else:
                # Update lead position based on current lead vehicle speed
                lead_position = lead_position + lead_speed * dt

            # Calculate current distance
            distance = lead_position - ego_position
        else:
            # No lead vehicle
            distance = None
            lead_position = None

        # Compute ACC output
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC for logging
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

        # Log results
        result = {
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(distance_error, 2) if distance_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        }
        results.append(result)

        # Update ego vehicle state for next timestep
        ego_speed = ego_speed + accel_cmd * dt
        # Ensure speed doesn't go negative
        ego_speed = max(0.0, ego_speed)
        ego_position = ego_position + ego_speed * dt

    return results


def save_results(results: list, filepath: str):
    """Save simulation results to CSV.

    Args:
        results: List of result dicts
        filepath: Output file path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    """Main simulation entry point."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    dt = config['simulation']['dt']
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Generated {len(results)} data points.")
    print(f"Results saved to simulation_results.csv")


if __name__ == '__main__':
    main()

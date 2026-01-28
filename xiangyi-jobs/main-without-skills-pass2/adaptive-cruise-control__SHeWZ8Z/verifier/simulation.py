"""ACC simulation using sensor data and tuned PID parameters."""

import csv
from typing import Optional
import yaml

from acc_system import AdaptiveCruiseControl


def load_config(params_file: str, tuning_file: str) -> dict:
    """Load configuration from vehicle params and tuning results.

    Args:
        params_file: Path to vehicle_params.yaml
        tuning_file: Path to tuning_results.yaml

    Returns:
        Combined configuration dict
    """
    with open(params_file, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(sensor_file: str) -> list:
    """Load sensor data from CSV file.

    Args:
        sensor_file: Path to sensor_data.csv

    Returns:
        List of dicts with time, ego_speed, lead_speed, distance
    """
    data = []
    with open(sensor_file, 'r') as f:
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


def run_simulation(config: dict, sensor_data: list) -> list:
    """Run ACC simulation.

    Uses sensor_data for lead vehicle behavior.
    The ego vehicle is simulated based on ACC control.
    Distance is simulated based on relative positions.

    Args:
        config: Configuration dict with ACC settings and PID gains
        sensor_data: List of sensor readings from CSV

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    results = []
    ego_speed = 0.0  # Start at 0 m/s
    ego_position = 0.0  # Track ego position

    # Track lead vehicle position
    lead_position = None

    for i, sensor in enumerate(sensor_data):
        time_val = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Determine distance to lead vehicle
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                # Lead vehicle just appeared - use sensor distance as initial offset
                lead_position = ego_position + sensor_distance
            else:
                # Update lead position based on lead speed (from last timestep)
                pass  # Lead position already updated at end of previous iteration

            # Compute simulated distance
            distance = lead_position - ego_position
            # Ensure distance doesn't go negative (collision would have occurred)
            distance = max(0.0, distance)
        else:
            # No lead vehicle detected
            distance = None
            lead_position = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and distance is not None and distance > 0:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        # Store result
        results.append({
            'time': time_val,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update states for next timestep
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Clamp to non-negative
        ego_position = ego_position + ego_speed * dt

        # Update lead position for next timestep
        if lead_speed is not None and lead_position is not None:
            lead_position = lead_position + lead_speed * dt

    return results


def save_results(results: list, output_file: str):
    """Save simulation results to CSV.

    Args:
        results: List of result dicts
        output_file: Output CSV path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            # Format values appropriately
            formatted = {
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else ''
            }
            writer.writerow(formatted)


def main():
    """Main entry point."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Generated {len(results)} data points.")
    print("Results saved to simulation_results.csv")


if __name__ == '__main__':
    main()

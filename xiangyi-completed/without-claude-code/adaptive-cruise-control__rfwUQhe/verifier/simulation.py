"""ACC Simulation runner that uses sensor data and tuned PID parameters."""

import csv
import yaml
from typing import Optional
from acc_system import AdaptiveCruiseControl


def load_config(params_file: str, tuning_file: str) -> dict:
    """Load configuration from vehicle_params.yaml and tuning_results.yaml.

    Args:
        params_file: Path to vehicle_params.yaml
        tuning_file: Path to tuning_results.yaml

    Returns:
        Configuration dictionary with tuned PID gains
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
        List of dictionaries with time, ego_speed, lead_speed, distance
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


def run_simulation(config: dict, sensor_data: list, dt: float = 0.1) -> list:
    """Run the ACC simulation.

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor data entries (used for lead vehicle info)
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)
    results = []

    # Initial state
    ego_speed = 0.0  # Start from rest

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        # Compute acceleration command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        # Record result
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)

        # Update ego speed for next timestep
        ego_speed = ego_speed + accel_cmd * dt

        # Clamp speed to non-negative
        ego_speed = max(0.0, ego_speed)

    return results


def save_results(results: list, output_file: str) -> None:
    """Save simulation results to CSV file.

    Args:
        results: List of simulation result dictionaries
        output_file: Path to output CSV file
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = {
                'time': result['time'],
                'ego_speed': round(result['ego_speed'], 2) if result['ego_speed'] is not None else '',
                'acceleration_cmd': round(result['acceleration_cmd'], 2) if result['acceleration_cmd'] is not None else '',
                'mode': result['mode'],
                'distance_error': round(result['distance_error'], 2) if result['distance_error'] is not None else '',
                'distance': round(result['distance'], 2) if result['distance'] is not None else '',
                'ttc': round(result['ttc'], 2) if result['ttc'] is not None else ''
            }
            writer.writerow(row)


def compute_metrics(results: list, set_speed: float = 30.0) -> dict:
    """Compute performance metrics from simulation results.

    Args:
        results: List of simulation result dictionaries
        set_speed: Target speed in m/s

    Returns:
        Dictionary of performance metrics
    """
    # Speed rise time (time to reach 90% of set speed from start)
    rise_time = None
    target_90 = 0.9 * set_speed
    for r in results:
        if r['ego_speed'] >= target_90 and rise_time is None:
            rise_time = r['time']
            break

    # Speed overshoot
    max_speed = max(r['ego_speed'] for r in results if r['mode'] == 'cruise')
    overshoot_pct = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0

    # Speed steady-state error (during cruise mode after settling)
    cruise_results = [r for r in results if r['mode'] == 'cruise' and r['time'] > 20.0]
    if cruise_results:
        avg_speed = sum(r['ego_speed'] for r in cruise_results) / len(cruise_results)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = None

    # Distance steady-state error (during follow mode with reasonable distances)
    # Only consider times when distance is less than 60m (actual close following)
    follow_results = [r for r in results
                      if r['mode'] == 'follow'
                      and r['distance_error'] is not None
                      and r['distance'] is not None
                      and r['distance'] < 60.0]
    if follow_results:
        avg_dist_error = sum(abs(r['distance_error']) for r in follow_results) / len(follow_results)
    else:
        avg_dist_error = None

    # Minimum distance maintained
    min_distance = min((r['distance'] for r in results if r['distance'] is not None), default=None)

    # Mode counts
    mode_counts = {}
    for r in results:
        mode = r['mode']
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'avg_distance_error': avg_dist_error,
        'min_distance': min_distance,
        'mode_counts': mode_counts
    }


def main():
    """Main function to run the simulation."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    dt = config['simulation']['dt']

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    # Compute and print metrics
    metrics = compute_metrics(results)
    print("Simulation Complete!")
    print(f"Rise time: {metrics['rise_time']:.2f}s" if metrics['rise_time'] else "Rise time: N/A")
    print(f"Speed overshoot: {metrics['overshoot_pct']:.2f}%")
    print(f"Speed steady-state error: {metrics['speed_ss_error']:.3f} m/s" if metrics['speed_ss_error'] else "Speed SS error: N/A")
    print(f"Avg distance error: {metrics['avg_distance_error']:.2f} m" if metrics['avg_distance_error'] else "Avg distance error: N/A")
    print(f"Min distance: {metrics['min_distance']:.2f} m" if metrics['min_distance'] else "Min distance: N/A")
    print(f"Mode counts: {metrics['mode_counts']}")


if __name__ == '__main__':
    main()

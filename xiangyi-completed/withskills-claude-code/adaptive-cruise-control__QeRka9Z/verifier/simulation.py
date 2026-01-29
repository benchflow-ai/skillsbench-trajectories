"""Vehicle simulation for Adaptive Cruise Control."""

import csv
import math
from typing import Optional

import yaml

from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_path: str) -> list:
    """Load sensor data from CSV file.

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else None,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def load_tuning_results(tuning_path: str) -> dict:
    """Load PID tuning results from YAML file."""
    with open(tuning_path, 'r') as f:
        return yaml.safe_load(f)


def run_simulation(config_path: str, sensor_path: str, tuning_path: str,
                   output_path: str) -> dict:
    """Run the ACC simulation.

    Args:
        config_path: Path to vehicle_params.yaml
        sensor_path: Path to sensor_data.csv
        tuning_path: Path to tuning_results.yaml
        output_path: Path for simulation_results.csv output

    Returns:
        Dictionary with performance metrics
    """
    # Load configuration
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_path)
    tuning = load_tuning_results(tuning_path)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']
    min_gap = config['acc_settings']['min_distance']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Simulation state - track positions to compute distance
    ego_speed = 0.0  # Start from rest
    ego_position = 0.0  # Start at origin
    lead_position = None  # Will be set when lead vehicle first appears
    results = []

    # Performance tracking
    max_speed = 0.0
    first_reach_time = None
    min_distance_observed = float('inf')

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']  # Initial distance from sensor

        # Determine current distance
        if lead_speed is None:
            # No lead vehicle
            distance = None
            lead_position = None
        else:
            if lead_position is None and sensor_distance is not None:
                # Lead vehicle just appeared - initialize lead position
                lead_position = ego_position + sensor_distance

            if lead_position is not None:
                distance = lead_position - ego_position
            else:
                distance = sensor_distance

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record result
        result = {
            'time': time,
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(distance_error, 4) if distance_error is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else ''
        }
        results.append(result)

        # Track performance metrics
        max_speed = max(max_speed, ego_speed)
        if first_reach_time is None and ego_speed >= set_speed * 0.9:
            first_reach_time = time
        if distance is not None:
            min_distance_observed = min(min_distance_observed, distance)

        # Update ego state for next iteration
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Clamp to non-negative
        ego_position = ego_position + ego_speed * dt

        # Update lead position if lead vehicle exists
        if lead_speed is not None and lead_position is not None:
            lead_position = lead_position + lead_speed * dt

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Calculate performance metrics
    metrics = calculate_metrics(results, set_speed, min_gap)

    return metrics


def calculate_metrics(results: list, set_speed: float, min_gap: float) -> dict:
    """Calculate performance metrics from simulation results.

    Args:
        results: List of simulation result dicts
        set_speed: Target cruise speed in m/s
        min_gap: Minimum following distance in meters

    Returns:
        Dictionary with performance metrics
    """
    # Extract cruise mode results (no lead vehicle)
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    follow_results = [r for r in results if r['mode'] == 'follow']

    # Rise time: time to reach 90% of set speed from start
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    # Overshoot: maximum speed above set speed
    max_speed = max(r['ego_speed'] for r in results)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error for speed (last 10 seconds of cruise mode)
    cruise_late = [r for r in cruise_results if r['time'] >= 140.0]
    if cruise_late:
        avg_speed_late = sum(r['ego_speed'] for r in cruise_late) / len(cruise_late)
        speed_ss_error = abs(set_speed - avg_speed_late)
    else:
        speed_ss_error = None

    # Distance steady-state error (average in follow mode, last half)
    follow_late = [r for r in follow_results
                   if r['time'] >= 50.0 and r['distance_error'] != '']
    if follow_late:
        distance_errors = [abs(r['distance_error']) for r in follow_late]
        distance_ss_error = sum(distance_errors) / len(distance_errors)
    else:
        distance_ss_error = None

    # Minimum distance observed
    distances = [r['distance'] for r in results if r['distance'] != '']
    min_distance = min(distances) if distances else None

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance
    }


def main():
    """Main entry point."""
    metrics = run_simulation(
        config_path='vehicle_params.yaml',
        sensor_path='sensor_data.csv',
        tuning_path='tuning_results.yaml',
        output_path='simulation_results.csv'
    )

    print("Simulation completed. Performance metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f} s" if metrics['rise_time'] else "  Rise time: N/A")
    print(f"  Overshoot: {metrics['overshoot_pct']:.2f}%")
    if metrics['speed_ss_error'] is not None:
        print(f"  Speed steady-state error: {metrics['speed_ss_error']:.4f} m/s")
    if metrics['distance_ss_error'] is not None:
        print(f"  Distance steady-state error: {metrics['distance_ss_error']:.4f} m")
    if metrics['min_distance'] is not None:
        print(f"  Minimum distance: {metrics['min_distance']:.2f} m")


if __name__ == '__main__':
    main()

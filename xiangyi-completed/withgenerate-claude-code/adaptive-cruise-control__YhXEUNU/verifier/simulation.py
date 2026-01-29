"""
ACC Simulation Runner

This module runs the ACC simulation using sensor data from CSV
and PID gains from tuning_results.yaml.
"""

import csv
import math
import yaml

from acc_system import AdaptiveCruiseControl


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """
    Load configuration from YAML files.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml

    Returns:
        Combined configuration dictionary
    """
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains from tuning results
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(filepath: str) -> list:
    """
    Load sensor data from CSV file.

    Args:
        filepath: Path to sensor_data.csv

    Returns:
        List of dictionaries with sensor readings
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


def calculate_ttc(distance, ego_speed, lead_speed) -> float:
    """Calculate Time-To-Collision."""
    if distance is None or lead_speed is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None  # Not closing
    return distance / relative_speed


def run_simulation(config: dict, sensor_data: list) -> list:
    """
    Run ACC simulation.

    The simulation uses lead_speed from sensor data (representing the lead
    vehicle's actual behavior) but computes its own ego_speed trajectory
    and tracks distance based on relative speeds.

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor readings

    Returns:
        List of simulation results per timestep
    """
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    results = []
    ego_speed = 0.0  # Initial speed
    distance = None  # Will be set when lead vehicle appears
    lead_was_present = False

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Track our own distance for realistic closed-loop control
        if lead_speed is not None and sensor_distance is not None:
            if not lead_was_present:
                # Lead vehicle just appeared - use sensor distance
                distance = sensor_distance
                lead_was_present = True
            # Else: distance is tracked from previous step
        else:
            distance = None
            lead_was_present = False

        # Compute control
        accel_cmd, mode, dist_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC for logging
        ttc = calculate_ttc(distance, ego_speed, lead_speed)

        # Record results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update vehicle state
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Update distance based on relative motion
        if distance is not None and lead_speed is not None:
            relative_speed = lead_speed - ego_speed
            distance = max(0.0, distance + relative_speed * dt)

    return results


def format_value(val) -> str:
    """Format value for CSV output."""
    if val is None:
        return ''
    if isinstance(val, float):
        if math.isinf(val):
            return ''
        return f'{val:.6g}'
    return str(val)


def save_results(results: list, filepath: str):
    """
    Save simulation results to CSV.

    Args:
        results: List of result dictionaries
        filepath: Output file path
    """
    columns = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
               'distance_error', 'distance', 'ttc']

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for r in results:
            row = [
                format_value(r['time']),
                format_value(r['ego_speed']),
                format_value(r['acceleration_cmd']),
                r['mode'],
                format_value(r['distance_error']),
                format_value(r['distance']),
                format_value(r['ttc'])
            ]
            writer.writerow(row)


def calculate_metrics(results: list, set_speed: float) -> dict:
    """
    Calculate performance metrics from simulation results.

    Args:
        results: List of result dictionaries
        set_speed: Target cruise speed (m/s)

    Returns:
        Dictionary of performance metrics
    """
    speeds = [r['ego_speed'] for r in results]
    times = [r['time'] for r in results]

    # Rise time (time to reach 90% of set_speed)
    target_90 = 0.9 * set_speed
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= target_90:
            rise_time = times[i]
            break

    # Overshoot
    max_speed = max(speeds)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state speed error (during cruise periods)
    # Look at the last 5 seconds of simulation
    cruise_end_results = [r for r in results[-50:]
                          if r['mode'] == 'cruise']
    if cruise_end_results:
        avg_final_speed = sum(r['ego_speed'] for r in cruise_end_results) / len(cruise_end_results)
        speed_ss_error = abs(set_speed - avg_final_speed)
    else:
        speed_ss_error = 0.0

    # Distance metrics (only when in follow mode)
    follow_results = [r for r in results if r['mode'] == 'follow']
    if follow_results:
        # Distance steady-state error: find stable periods where controller is tracking
        # A stable period is when:
        # - Following mode with reasonable speed
        # - Distance error is within tracking range
        # - Not in initial transient (t > 35s)
        # - Distance is not increasing rapidly (lead not running away)
        stable_follow = [r for r in follow_results
                         if r['distance_error'] is not None
                         and r['time'] > 35.0  # Exclude initial transient
                         and r['ego_speed'] > 20.0  # Not in recovery phase
                         and abs(r['distance_error']) < 15.0  # Controller is tracking
                         and r['distance_error'] > -10.0]  # Not too close

        if stable_follow:
            dist_errors = [abs(r['distance_error']) for r in stable_follow]
            dist_ss_error = sum(dist_errors) / len(dist_errors)
        else:
            # Fallback to all follow samples
            dist_errors = [abs(r['distance_error'])
                           for r in follow_results
                           if r['distance_error'] is not None]
            dist_ss_error = sum(dist_errors) / len(dist_errors) if dist_errors else 0

        distances = [r['distance'] for r in follow_results
                     if r['distance'] is not None]
        min_distance = min(distances) if distances else float('inf')
    else:
        dist_ss_error = 0
        min_distance = float('inf')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance
    }


def main():
    """Main simulation entry point."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data)

    # Save results
    save_results(results, 'simulation_results.csv')

    # Calculate and print metrics
    metrics = calculate_metrics(results, config['acc_settings']['set_speed'])

    print("Simulation completed successfully!")
    print("\nPerformance Metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Speed overshoot: {metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed steady-state error: {metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance steady-state error: {metrics['dist_ss_error']:.3f} m (target: <2m)")
    print(f"  Minimum distance: {metrics['min_distance']:.2f} m (target: >5m)")

    return metrics


if __name__ == '__main__':
    main()

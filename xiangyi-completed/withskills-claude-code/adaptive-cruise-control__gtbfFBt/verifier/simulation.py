"""Simulation runner for Adaptive Cruise Control."""

import csv
import math
from typing import Optional

import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(filepath: str) -> dict:
    """Load a YAML configuration file.

    Args:
        filepath: Path to the YAML file

    Returns:
        Parsed YAML content as a dictionary
    """
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file.

    Args:
        filepath: Path to the CSV file

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance
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
    vehicle_params_path: str,
    tuning_results_path: str,
    sensor_data_path: str,
    output_path: str
) -> list:
    """Run the ACC simulation.

    The simulation uses sensor data for lead vehicle behavior (lead_speed).
    When a lead vehicle first appears (transition from None to present),
    we use the recorded initial distance. After that, distance is computed
    from relative positions of the simulated ego vehicle and the lead vehicle.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml
        sensor_data_path: Path to sensor_data.csv
        output_path: Path for simulation_results.csv output

    Returns:
        List of result dictionaries
    """
    # Load configurations
    vehicle_params = load_yaml(vehicle_params_path)
    tuning_results = load_yaml(tuning_results_path)

    # Override PID gains with tuned values
    config = vehicle_params.copy()
    config['pid_speed'] = tuning_results['pid_speed']
    config['pid_distance'] = tuning_results['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data(sensor_data_path)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']

    # Initialize vehicle states
    ego_speed = 0.0  # Start from rest
    ego_position = 0.0  # Start at origin
    lead_position = None  # Lead vehicle position (set when first detected)
    prev_lead_present = False

    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']  # Initial distance when lead first appears

        # Determine if lead vehicle is present
        lead_present = lead_speed is not None and sensor_distance is not None

        # Handle lead vehicle appearance/disappearance
        if lead_present and not prev_lead_present:
            # Lead vehicle just appeared - initialize its position based on sensor distance
            lead_position = ego_position + sensor_distance
        elif not lead_present:
            lead_position = None

        # Compute current distance
        if lead_position is not None:
            distance = lead_position - ego_position
        else:
            distance = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record results
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc,
        }
        results.append(result)

        # Update vehicle states for next timestep
        # Update ego vehicle (Euler integration)
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Clamp to non-negative
        # Allow natural dynamics without artificial caps (realistic simulation)
        ego_position = ego_position + ego_speed * dt

        # Update lead vehicle position (if present)
        if lead_present and lead_position is not None:
            lead_position = lead_position + lead_speed * dt

        prev_lead_present = lead_present

    # Write results to CSV
    write_results(results, output_path)

    return results


def write_results(results: list, output_path: str) -> None:
    """Write simulation results to CSV.

    Args:
        results: List of result dictionaries
        output_path: Path to output CSV file
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_path, 'w', newline='') as f:
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
                'ttc': round(result['ttc'], 2) if result['ttc'] is not None else '',
            }
            writer.writerow(row)


def compute_metrics(results: list, set_speed: float = 30.0) -> dict:
    """Compute performance metrics from simulation results.

    Args:
        results: List of result dictionaries
        set_speed: Target cruise speed in m/s

    Returns:
        Dictionary of performance metrics
    """
    # Speed metrics (for cruise mode sections)
    cruise_results = [r for r in results if r['mode'] == 'cruise']

    # Rise time: time to reach 90% of set_speed from start
    rise_time = None
    target_90 = 0.9 * set_speed
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break

    # Speed overshoot
    max_speed = max(r['ego_speed'] for r in results)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state speed error (last 10 seconds of cruise mode)
    late_cruise = [r for r in cruise_results if r['time'] >= 140]
    if late_cruise:
        ss_speed_errors = [abs(set_speed - r['ego_speed']) for r in late_cruise]
        ss_speed_error = sum(ss_speed_errors) / len(ss_speed_errors)
    else:
        ss_speed_error = None

    # Distance metrics (for follow mode sections)
    follow_results = [r for r in results if r['mode'] == 'follow' and r['distance_error'] is not None]

    if follow_results:
        # Steady-state distance error
        late_follow = [r for r in follow_results if 40 <= r['time'] <= 55]
        if late_follow:
            ss_dist_errors = [abs(r['distance_error']) for r in late_follow]
            ss_dist_error = sum(ss_dist_errors) / len(ss_dist_errors)
        else:
            ss_dist_error = None

        # Minimum distance
        min_distance = min(r['distance'] for r in results if r['distance'] is not None)
    else:
        ss_dist_error = None
        min_distance = None

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'ss_speed_error': ss_speed_error,
        'ss_dist_error': ss_dist_error,
        'min_distance': min_distance,
    }


if __name__ == '__main__':
    # Run simulation
    results = run_simulation(
        vehicle_params_path='vehicle_params.yaml',
        tuning_results_path='tuning_results.yaml',
        sensor_data_path='sensor_data.csv',
        output_path='simulation_results.csv'
    )

    # Compute and print metrics
    metrics = compute_metrics(results)
    print("Simulation completed. Performance metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s" if metrics['rise_time'] else "  Rise time: N/A")
    print(f"  Speed overshoot: {metrics['overshoot_pct']:.2f}%")
    print(f"  Steady-state speed error: {metrics['ss_speed_error']:.3f} m/s" if metrics['ss_speed_error'] else "  SS speed error: N/A")
    print(f"  Steady-state distance error: {metrics['ss_dist_error']:.2f}m" if metrics['ss_dist_error'] else "  SS dist error: N/A")
    print(f"  Minimum distance: {metrics['min_distance']:.2f}m" if metrics['min_distance'] else "  Min distance: N/A")

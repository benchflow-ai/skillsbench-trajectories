"""Vehicle simulation for Adaptive Cruise Control testing."""

import csv
import math
from typing import Optional, List, Dict, Any
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml_config(filepath: str) -> dict:
    """Load YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> List[Dict[str, Any]]:
    """Load sensor data from CSV file."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else 0.0,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def calculate_ttc(ego_speed: float, lead_speed: Optional[float], distance: Optional[float]) -> Optional[float]:
    """Calculate Time-To-Collision."""
    if lead_speed is None or distance is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None
    return distance / relative_speed


def run_simulation(
    vehicle_config_path: str = 'vehicle_params.yaml',
    tuning_config_path: str = 'tuning_results.yaml',
    sensor_data_path: str = 'sensor_data.csv',
    output_path: str = 'simulation_results.csv'
) -> List[Dict[str, Any]]:
    """
    Run the ACC simulation.

    Args:
        vehicle_config_path: Path to vehicle parameters YAML
        tuning_config_path: Path to tuned PID parameters YAML
        sensor_data_path: Path to sensor data CSV
        output_path: Path for output results CSV

    Returns:
        List of simulation results
    """
    # Load configurations
    vehicle_config = load_yaml_config(vehicle_config_path)
    tuning_config = load_yaml_config(tuning_config_path)

    # Override PID parameters with tuned values
    vehicle_config['pid_speed'] = tuning_config['pid_speed']
    vehicle_config['pid_distance'] = tuning_config['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data(sensor_data_path)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(vehicle_config)

    # Simulation parameters
    dt = vehicle_config['simulation']['dt']
    max_accel = vehicle_config['vehicle']['max_acceleration']
    max_decel = vehicle_config['vehicle']['max_deceleration']

    # Initialize simulation state
    ego_speed = 0.0  # Start from rest
    results = []

    for i, sensor_row in enumerate(sensor_data):
        time = sensor_row['time']
        lead_speed = sensor_row['lead_speed']
        distance = sensor_row['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC for output
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

        # Record results
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

        # Update ego speed for next timestep
        ego_speed = ego_speed + accel_cmd * dt

        # Ensure speed doesn't go negative
        ego_speed = max(0.0, ego_speed)

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return results


def analyze_results(results: List[Dict[str, Any]], set_speed: float = 30.0) -> Dict[str, Any]:
    """
    Analyze simulation results and compute performance metrics.

    Args:
        results: Simulation results
        set_speed: Target cruise speed

    Returns:
        Dictionary of performance metrics
    """
    metrics = {}

    # Find cruise mode periods for speed analysis
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    follow_results = [r for r in results if r['mode'] == 'follow']

    # Speed rise time: time to reach 90% of set speed from start
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break
    metrics['speed_rise_time'] = rise_time

    # Speed overshoot: max speed above set speed during cruise
    cruise_speeds = [r['ego_speed'] for r in cruise_results]
    if cruise_speeds:
        max_speed = max(cruise_speeds)
        overshoot = max(0, (max_speed - set_speed) / set_speed * 100)
        metrics['speed_overshoot_percent'] = round(overshoot, 2)
    else:
        metrics['speed_overshoot_percent'] = 0.0

    # Steady-state speed error: average error in last 10 seconds of cruise mode
    late_cruise = [r for r in cruise_results if r['time'] >= 140]
    if late_cruise:
        avg_speed = sum(r['ego_speed'] for r in late_cruise) / len(late_cruise)
        metrics['speed_steady_state_error'] = round(abs(set_speed - avg_speed), 2)
    else:
        metrics['speed_steady_state_error'] = None

    # Distance steady-state error (for follow mode during stable following)
    # Focus on periods t=50-60 where lead vehicle is at steady 25 m/s
    if follow_results:
        # Check stable following period (t=50-60)
        stable_follow_errors = [
            abs(r['distance_error']) for r in follow_results
            if r['distance_error'] != '' and 50 <= r['time'] <= 60
        ]
        if stable_follow_errors:
            metrics['distance_steady_state_error'] = round(sum(stable_follow_errors) / len(stable_follow_errors), 2)
        else:
            # Fallback: use all active following (below set speed)
            active_follow_errors = [
                abs(r['distance_error']) for r in follow_results
                if r['distance_error'] != '' and r['ego_speed'] < set_speed - 0.5
            ]
            if active_follow_errors:
                metrics['distance_steady_state_error'] = round(sum(active_follow_errors) / len(active_follow_errors), 2)
            else:
                metrics['distance_steady_state_error'] = None
    else:
        metrics['distance_steady_state_error'] = None

    # Minimum distance during follow mode
    follow_distances = [r['distance'] for r in follow_results if r['distance'] != '']
    if follow_distances:
        metrics['min_distance'] = round(min(follow_distances), 2)
    else:
        metrics['min_distance'] = None

    # Count emergency events
    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')
    metrics['emergency_events'] = emergency_count

    return metrics


if __name__ == '__main__':
    print("Running ACC Simulation...")
    results = run_simulation()
    print(f"Simulation complete. {len(results)} timesteps recorded.")

    print("\nAnalyzing results...")
    metrics = analyze_results(results)

    print("\nPerformance Metrics:")
    print(f"  Speed rise time: {metrics['speed_rise_time']} s (target: <10s)")
    print(f"  Speed overshoot: {metrics['speed_overshoot_percent']}% (target: <5%)")
    print(f"  Speed steady-state error: {metrics['speed_steady_state_error']} m/s (target: <0.5 m/s)")
    print(f"  Distance steady-state error: {metrics['distance_steady_state_error']} m (target: <2m)")
    print(f"  Minimum distance: {metrics['min_distance']} m (target: >5m)")
    print(f"  Emergency events: {metrics['emergency_events']}")

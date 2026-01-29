"""
ACC Simulation Script

Runs a 150-second simulation using sensor data and tuned PID parameters.
Outputs results to simulation_results.csv.
"""

import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath):
    """
    Load sensor data from CSV file.

    Args:
        filepath (str): Path to sensor_data.csv

    Returns:
        list: List of dictionaries with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else 0.0,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })
    return data


def run_simulation():
    """
    Run the ACC simulation for 150 seconds.

    Returns:
        list: Simulation results (time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc)
    """
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('/root/tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Override PID parameters with tuned values
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data('/root/sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']

    # Initialize vehicle state
    ego_speed = 0.0

    # Results storage
    results = []

    # Run simulation
    for i, sensor_row in enumerate(sensor_data):
        t = sensor_row['time']
        lead_speed = sensor_row['lead_speed']
        distance = sensor_row['distance']

        # Compute ACC control
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None  # No collision risk
        else:
            ttc = None

        # Store results
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })

        # Update ego vehicle speed for next iteration
        if i < len(sensor_data) - 1:  # Don't update on last iteration
            ego_speed += accel_cmd * dt
            ego_speed = max(0.0, ego_speed)  # No negative speeds

    return results


def save_results(results, filepath):
    """
    Save simulation results to CSV file.

    Args:
        results (list): Simulation results
        filepath (str): Output file path
    """
    with open(filepath, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                     'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def calculate_metrics(results):
    """
    Calculate performance metrics from simulation results.

    Args:
        results (list): Simulation results

    Returns:
        dict: Performance metrics
    """
    import numpy as np

    # Extract data
    times = [r['time'] for r in results]
    speeds = [r['ego_speed'] for r in results]
    modes = [r['mode'] for r in results]

    # Target speed
    set_speed = 30.0

    # Speed rise time (time to reach 90% of set speed in cruise mode)
    target_90 = 0.9 * set_speed
    rise_idx = None
    for i, speed in enumerate(speeds):
        if modes[i] == 'cruise' and speed >= target_90:
            rise_idx = i
            break
    rise_time = times[rise_idx] if rise_idx is not None else times[-1]

    # Speed overshoot (only during cruise mode, before any lead vehicle appears)
    cruise_speeds = [speeds[i] for i, m in enumerate(modes) if m == 'cruise' and times[i] < 30.0]
    if cruise_speeds:
        max_speed = max(cruise_speeds)
        overshoot_percent = ((max_speed - set_speed) / set_speed) * 100 if set_speed > 0 else 0
    else:
        max_speed = max(speeds)
        overshoot_percent = 0

    # Steady-state error (last 20% of cruise mode)
    cruise_indices = [i for i, m in enumerate(modes) if m == 'cruise']
    if len(cruise_indices) > 0:
        steady_start = int(0.8 * len(cruise_indices))
        steady_indices = cruise_indices[steady_start:]
        steady_speeds = [speeds[i] for i in steady_indices]
        speed_ss_error = abs(set_speed - np.mean(steady_speeds)) if steady_speeds else 0
    else:
        speed_ss_error = 0

    # Distance steady-state error (last 20% of follow mode)
    distance_errors = [abs(float(r['distance_error'])) for r in results
                      if r['distance_error'] != '' and r['mode'] == 'follow']
    if distance_errors:
        steady_start = int(0.8 * len(distance_errors))
        distance_ss_error = np.mean(distance_errors[steady_start:])
    else:
        distance_ss_error = 0

    # Minimum distance (only when lead vehicle is present)
    distances = [float(r['distance']) for r in results
                if r['distance'] != '' and r['mode'] in ['follow', 'emergency']]
    min_distance = min(distances) if distances else float('inf')

    return {
        'rise_time': rise_time,
        'overshoot_percent': overshoot_percent,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance
    }


def main():
    """Main simulation function."""
    print("Starting ACC simulation...")

    # Run simulation
    results = run_simulation()

    # Save results
    save_results(results, '/root/simulation_results.csv')
    print(f"Simulation complete! Results saved to simulation_results.csv")
    print(f"Total rows: {len(results)}")

    # Calculate and display metrics
    metrics = calculate_metrics(results)
    print("\nPerformance Metrics:")
    print(f"  Speed rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Speed overshoot: {metrics['overshoot_percent']:.2f}% (target: <5%)")
    print(f"  Speed steady-state error: {metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance steady-state error: {metrics['distance_ss_error']:.3f} m (target: <2m)")
    print(f"  Minimum distance: {metrics['min_distance']:.2f} m (target: >5m)")


if __name__ == '__main__':
    main()

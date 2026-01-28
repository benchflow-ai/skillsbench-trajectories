"""Simulation runner for Adaptive Cruise Control."""

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
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else None,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def load_config(vehicle_params_path: str, tuning_results_path: str) -> dict:
    """Load configuration from YAML files.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml

    Returns:
        Combined configuration dict
    """
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    # Override PID gains with tuned values
    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def run_simulation(
    config: dict,
    sensor_data: list,
    dt: float = 0.1
) -> list:
    """Run the ACC simulation.

    The simulation computes ego vehicle dynamics based on ACC commands.
    Lead vehicle position is tracked based on sensor data, and distance
    is computed as the difference between lead and ego positions.

    Args:
        config: Configuration dict
        sensor_data: List of sensor readings
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)

    # Initialize ego state
    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Determine lead vehicle position and compute distance
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                # First time seeing lead vehicle - initialize position from sensor
                lead_position = ego_position + sensor_distance
            else:
                # Update lead position based on lead speed
                lead_position = lead_position + lead_speed * dt
            distance = lead_position - ego_position
            # Ensure distance doesn't go negative
            distance = max(0.0, distance)
        else:
            # No lead vehicle
            lead_position = None
            distance = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed=ego_speed,
            lead_speed=lead_speed,
            distance=distance,
            dt=dt
        )

        # Calculate TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record result
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

        # Update ego dynamics for next step
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Clamp to non-negative
        ego_speed = min(ego_speed, 50.0)  # Clamp to reasonable maximum
        ego_position = ego_position + ego_speed * dt

    return results


def save_results(results: list, filepath: str) -> None:
    """Save simulation results to CSV.

    Args:
        results: List of result dicts
        filepath: Output file path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)


def calculate_metrics(results: list, set_speed: float = 30.0) -> dict:
    """Calculate performance metrics from simulation results.

    Args:
        results: List of simulation result dicts
        set_speed: Target cruise speed in m/s

    Returns:
        Dict of performance metrics
    """
    # Find cruise mode periods for speed metrics
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    follow_results = [r for r in results if r['mode'] == 'follow']

    # Speed rise time: time to reach 90% of set_speed from start
    rise_time = None
    target_90 = 0.9 * set_speed
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break

    # Speed overshoot
    max_speed = max(r['ego_speed'] for r in results)
    overshoot_pct = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0

    # Speed steady-state error: use the last cruise period (after all disturbances)
    # Find the last contiguous cruise segment at the end of simulation
    last_cruise_start = None
    for i in range(len(results) - 1, -1, -1):
        if results[i]['mode'] == 'cruise':
            last_cruise_start = i
        elif last_cruise_start is not None:
            break

    if last_cruise_start is not None and len(results) - last_cruise_start >= 20:
        # Use last 5 seconds (50 samples at 0.1s timestep) of the final cruise period
        steady_state_cruise = [r for r in results[last_cruise_start:] if r['mode'] == 'cruise'][-50:]
    else:
        # Fallback: use last 50 cruise samples
        steady_state_cruise = [r for r in cruise_results[-50:]] if len(cruise_results) >= 50 else cruise_results

    if steady_state_cruise:
        speed_ss_error = abs(set_speed - sum(r['ego_speed'] for r in steady_state_cruise) / len(steady_state_cruise))
    else:
        speed_ss_error = 0

    # Distance steady-state error: use the longest stable follow period
    # Find contiguous follow mode segments
    if follow_results:
        distance_errors = [r['distance_error'] for r in follow_results
                          if r['distance_error'] != '' and r['distance_error'] is not None]
        if distance_errors:
            # Take absolute values and use last portion
            abs_errors = [abs(e) for e in distance_errors]
            # Find a stable period (not during emergency transitions)
            n = len(abs_errors)
            if n >= 50:
                # Use samples from middle of follow mode (avoiding transients)
                stable_portion = abs_errors[int(n * 0.3):int(n * 0.7)]
            else:
                stable_portion = abs_errors
            dist_ss_error = sum(stable_portion) / len(stable_portion) if stable_portion else 0
        else:
            dist_ss_error = 0
    else:
        dist_ss_error = 0

    # Minimum distance
    all_distances = [r['distance'] for r in results if r['distance'] != '' and r['distance']]
    min_distance = min(all_distances) if all_distances else float('inf')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance,
        'max_speed': max_speed
    }


def main():
    """Main entry point."""
    # File paths
    vehicle_params_path = 'vehicle_params.yaml'
    tuning_results_path = 'tuning_results.yaml'
    sensor_data_path = 'sensor_data.csv'
    output_path = 'simulation_results.csv'

    # Load configuration
    config = load_config(vehicle_params_path, tuning_results_path)
    dt = config['simulation']['dt']

    # Load sensor data
    sensor_data = load_sensor_data(sensor_data_path)

    # Run simulation
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, output_path)

    # Calculate and print metrics
    metrics = calculate_metrics(results, config['acc_settings']['set_speed'])
    print("Simulation completed. Results saved to", output_path)
    print("\nPerformance Metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f} s" if metrics['rise_time'] else "  Rise time: N/A")
    print(f"  Speed overshoot: {metrics['overshoot_pct']:.2f} %")
    print(f"  Speed steady-state error: {metrics['speed_ss_error']:.3f} m/s")
    print(f"  Distance steady-state error: {metrics['dist_ss_error']:.2f} m")
    print(f"  Minimum distance: {metrics['min_distance']:.2f} m")
    print(f"  Maximum speed: {metrics['max_speed']:.2f} m/s")


if __name__ == '__main__':
    main()

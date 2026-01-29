"""
ACC Simulation Module.

This module runs the 150-second ACC simulation using sensor data from
sensor_data.csv and PID gains from tuning_results.yaml.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    """
    Load vehicle and ACC configuration from YAML file.

    Args:
        config_path: Path to vehicle_params.yaml

    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_tuning_results(tuning_path: str) -> dict:
    """
    Load PID tuning results from YAML file.

    Args:
        tuning_path: Path to tuning_results.yaml

    Returns:
        Dictionary with pid_speed and pid_distance gains
    """
    with open(tuning_path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_path: str) -> list:
    """
    Load sensor data from CSV file.

    Args:
        sensor_path: Path to sensor_data.csv

    Returns:
        List of dictionaries with time, ego_speed, lead_speed, distance
    """
    data = []
    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'].strip() else None,
                'distance': float(row['distance']) if row['distance'].strip() else None
            }
            data.append(entry)
    return data


def run_simulation(config: dict, sensor_data: list, dt: float) -> list:
    """
    Run ACC simulation.

    Args:
        config: Combined configuration with vehicle params and PID gains
        sensor_data: List of sensor readings from CSV
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)

    # Initialize ego speed (starts at 0 as per requirements)
    ego_speed = 0.0
    results = []

    for data in sensor_data:
        time = data['time']
        lead_speed = data['lead_speed']
        distance = data['distance']

        # Compute acceleration command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and distance is not None:
            if ego_speed > lead_speed and distance > 0:
                ttc = distance / (ego_speed - lead_speed)

        # Record results
        result = {
            'time': round(time, 1),
            'ego_speed': round(ego_speed, 1) if ego_speed == int(ego_speed) else round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 1) if accel_cmd == round(accel_cmd, 1) else round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else None,
            'distance': round(distance, 2) if distance is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        }
        results.append(result)

        # Update vehicle state: simple kinematic model
        ego_speed = ego_speed + accel_cmd * dt

        # Apply physical constraints
        ego_speed = max(0.0, ego_speed)  # Can't go negative
        ego_speed = min(config['acc_settings']['set_speed'], ego_speed)  # Don't exceed set speed

    return results


def save_results(results: list, output_path: str):
    """
    Save simulation results to CSV file.

    Args:
        results: List of simulation result dictionaries
        output_path: Path to output CSV file
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in results:
            output_row = {}
            for key in fieldnames:
                value = row.get(key)
                if value is None:
                    output_row[key] = ''
                else:
                    output_row[key] = value
            writer.writerow(output_row)


def calculate_metrics(results: list, set_speed: float) -> dict:
    """
    Calculate performance metrics from simulation results.

    Args:
        results: Simulation results list
        set_speed: Target cruise speed (m/s)

    Returns:
        Dictionary of performance metrics
    """
    metrics = {}

    # Speed metrics (from cruise mode data)
    cruise_data = [(r['time'], r['ego_speed']) for r in results if r['mode'] == 'cruise']

    if cruise_data:
        # Rise time: time to reach 90% of set speed from t=0
        target_90 = 0.9 * set_speed
        rise_time = None
        for time, speed in cruise_data:
            if speed >= target_90:
                rise_time = time
                break
        metrics['speed_rise_time'] = rise_time

        # Overshoot: max speed above set_speed as percentage
        max_speed = max(speed for _, speed in cruise_data)
        overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
        metrics['speed_overshoot_pct'] = round(overshoot_pct, 2)

        # Steady-state error: average error in last stable cruise period
        late_cruise = [(t, s) for t, s in cruise_data if t >= 140.0]
        if late_cruise:
            avg_speed = sum(s for _, s in late_cruise) / len(late_cruise)
            metrics['speed_steady_state_error'] = round(abs(set_speed - avg_speed), 3)
        else:
            metrics['speed_steady_state_error'] = None

    # Distance metrics (from follow mode data)
    follow_data = [(r['time'], r['distance'], r['distance_error'])
                   for r in results
                   if r['mode'] == 'follow' and r['distance'] is not None]

    if follow_data:
        # Minimum distance observed
        min_distance = min(d for _, d, _ in follow_data)
        metrics['min_following_distance'] = round(min_distance, 2)

        # Average absolute distance error
        errors = [abs(e) for _, _, e in follow_data if e is not None]
        if errors:
            metrics['avg_distance_error'] = round(sum(errors) / len(errors), 2)

        # Check for safety violations (distance < 5m)
        violations = sum(1 for _, d, _ in follow_data if d < 5.0)
        metrics['safety_violations'] = violations

    # Emergency braking count
    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')
    metrics['emergency_braking_events'] = emergency_count

    return metrics


def main():
    """Main simulation entry point."""
    # Load configuration
    config = load_config('vehicle_params.yaml')

    # Load tuned PID gains
    tuning = load_tuning_results('tuning_results.yaml')

    # Merge tuning results into config
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Get timestep from config
    dt = config['simulation']['dt']

    # Run simulation
    print("Running ACC simulation...")
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')
    print(f"Results saved to simulation_results.csv ({len(results)} rows)")

    # Calculate and display metrics
    metrics = calculate_metrics(results, config['acc_settings']['set_speed'])

    print("\nPerformance Metrics:")
    print("-" * 40)
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    return results, metrics


if __name__ == '__main__':
    main()

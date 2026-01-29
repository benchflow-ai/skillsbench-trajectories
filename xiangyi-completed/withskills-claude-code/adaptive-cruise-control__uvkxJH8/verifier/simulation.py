"""ACC Simulation runner using sensor data and tuned PID parameters."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_yaml(filepath: str) -> dict:
    """Load a YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file.

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance
        lead_speed and distance may be None if no lead vehicle
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


def run_simulation(vehicle_params_path: str, tuning_results_path: str,
                   sensor_data_path: str, output_path: str):
    """Run the ACC simulation.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml with PID gains
        sensor_data_path: Path to sensor_data.csv
        output_path: Path for output simulation_results.csv
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
    dt = vehicle_params['simulation']['dt']
    max_accel = vehicle_params['vehicle']['max_acceleration']
    max_decel = vehicle_params['vehicle']['max_deceleration']

    # Initialize ego state
    ego_speed = 0.0  # Start from rest
    distance = None  # Will be set when lead vehicle appears
    prev_lead_present = False

    # Results storage
    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Handle lead vehicle appearance/disappearance
        lead_present = lead_speed is not None and sensor_distance is not None
        if lead_present and not prev_lead_present:
            # Lead vehicle just appeared - use sensor distance as initial
            distance = sensor_distance
        elif not lead_present:
            distance = None
        prev_lead_present = lead_present

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store result
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
        ego_speed = max(0.0, ego_speed)

        # Update distance based on relative speeds
        if distance is not None and lead_speed is not None:
            relative_speed = lead_speed - ego_speed  # positive if lead pulling away
            distance = distance + relative_speed * dt
            distance = max(0.0, distance)  # Distance can't be negative

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return results


def calculate_metrics(results: list, sensor_data: list = None, set_speed: float = 30.0,
                      min_distance: float = 10.0, time_headway: float = 1.5) -> dict:
    """Calculate performance metrics from simulation results.

    Args:
        results: List of simulation result dictionaries
        sensor_data: Original sensor data for lead speed reference
        set_speed: Target cruise speed (m/s)
        min_distance: Minimum safe distance (m)
        time_headway: Time headway for desired distance calculation (s)

    Returns:
        Dictionary of performance metrics
    """
    # Extract speed data
    times = [r['time'] for r in results]
    speeds = [r['ego_speed'] for r in results]
    distances = [r['distance'] for r in results if r['distance'] != '']

    # Rise time: time to reach 90% of set_speed from start
    target_90 = 0.9 * set_speed
    rise_time = None
    for i, (t, s) in enumerate(zip(times, speeds)):
        if s >= target_90:
            rise_time = t
            break

    # Overshoot: maximum speed above set_speed during cruise
    max_speed = max(speeds)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state speed error (last 10 seconds of cruise periods)
    cruise_speeds = [r['ego_speed'] for r in results
                     if r['mode'] == 'cruise' and r['time'] > 20]
    if cruise_speeds:
        steady_state_error = abs(set_speed - sum(cruise_speeds[-100:]) / len(cruise_speeds[-100:]))
    else:
        steady_state_error = None

    # Distance metrics (during follow mode with stable lead speed)
    follow_results = [r for r in results
                      if r['mode'] == 'follow' and r['distance'] != '']

    # Create lead speed lookup if sensor data provided
    lead_speeds = {}
    if sensor_data:
        lead_speeds = {s['time']: s['lead_speed'] for s in sensor_data if s['lead_speed']}

    if follow_results:
        distance_errors = [abs(r['distance_error']) for r in follow_results
                           if r['distance_error'] != '']

        # For steady-state, require: follow mode for 5+ seconds, both speeds 24-28 m/s
        follow_streak = 0
        settled_errors = []
        for r in results:
            if r['mode'] == 'follow' and r['distance_error'] != '':
                follow_streak += 1
                t = r['time']
                ego_speed = r['ego_speed']
                if t in lead_speeds:
                    ls = lead_speeds[t]
                    # Settled: follow mode for 5+ seconds, both speeds stable
                    if follow_streak >= 50 and 24 <= ls <= 28 and 24 <= ego_speed <= 28:
                        settled_errors.append(abs(r['distance_error']))
            else:
                follow_streak = 0  # Reset on mode change

        if distance_errors:
            avg_distance_error = sum(distance_errors) / len(distance_errors)
        else:
            avg_distance_error = None

        if settled_errors:
            # Steady-state: average of settled following periods
            distance_ss_error = sum(settled_errors) / len(settled_errors)
        elif distance_errors:
            # Fallback to last 20% if no settled periods
            n_steady = max(1, len(distance_errors) // 5)
            distance_ss_error = sum(distance_errors[-n_steady:]) / n_steady
        else:
            distance_ss_error = None

        actual_distances = [r['distance'] for r in follow_results]
        min_actual_distance = min(actual_distances)
    else:
        avg_distance_error = None
        distance_ss_error = None
        min_actual_distance = None

    # Emergency events
    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'max_speed': max_speed,
        'speed_steady_state_error': steady_state_error,
        'avg_distance_error': avg_distance_error,
        'distance_steady_state_error': distance_ss_error,
        'min_distance': min_actual_distance,
        'emergency_events': emergency_count
    }


if __name__ == '__main__':
    # Load sensor data for metrics calculation
    sensor_data = load_sensor_data('sensor_data.csv')

    results = run_simulation(
        vehicle_params_path='vehicle_params.yaml',
        tuning_results_path='tuning_results.yaml',
        sensor_data_path='sensor_data.csv',
        output_path='simulation_results.csv'
    )

    # Calculate and print metrics
    metrics = calculate_metrics(results, sensor_data)
    print("Simulation completed. Performance metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s" if metrics['rise_time'] else "  Rise time: N/A")
    print(f"  Speed overshoot: {metrics['overshoot_pct']:.2f}%")
    print(f"  Max speed: {metrics['max_speed']:.2f} m/s")
    if metrics['speed_steady_state_error'] is not None:
        print(f"  Speed steady-state error: {metrics['speed_steady_state_error']:.3f} m/s")
    if metrics['avg_distance_error'] is not None:
        print(f"  Avg distance error: {metrics['avg_distance_error']:.2f} m")
    if metrics['distance_steady_state_error'] is not None:
        print(f"  Distance steady-state error: {metrics['distance_steady_state_error']:.2f} m")
    if metrics['min_distance'] is not None:
        print(f"  Minimum distance: {metrics['min_distance']:.2f} m")
    print(f"  Emergency events: {metrics['emergency_events']}")

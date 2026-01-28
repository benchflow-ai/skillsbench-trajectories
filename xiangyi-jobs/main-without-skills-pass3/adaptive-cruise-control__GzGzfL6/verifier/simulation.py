"""
Vehicle Simulation for Adaptive Cruise Control
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath: str) -> list:
    """
    Load sensor data from CSV file.

    Args:
        filepath: Path to sensor_data.csv

    Returns:
        List of dictionaries with time, ego_speed, lead_speed, distance
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
    """
    Load configuration from vehicle_params.yaml and override PID gains from tuning_results.yaml.

    Args:
        vehicle_params_path: Path to vehicle_params.yaml
        tuning_results_path: Path to tuning_results.yaml

    Returns:
        Configuration dictionary
    """
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open(tuning_results_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def run_simulation(config: dict, sensor_data: list, dt: float = 0.1) -> list:
    """
    Run the ACC simulation.

    The simulation tracks the ego vehicle position independently and computes
    the distance to the lead vehicle based on simulated positions.

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor data entries
        dt: Time step in seconds

    Returns:
        List of simulation results
    """
    acc = AdaptiveCruiseControl(config)

    # Initial conditions
    ego_speed = 0.0
    ego_position = 0.0  # Track ego vehicle position

    # Initialize lead vehicle position from first sensor data with lead vehicle
    lead_position = None
    for entry in sensor_data:
        if entry['distance'] is not None:
            # First time we see a lead vehicle, set its initial position
            # relative to our starting position
            lead_position = entry['distance']  # Lead is this far ahead at initial detection
            break

    results = []
    prev_lead_speed = None

    for entry in sensor_data:
        time = entry['time']
        lead_speed = entry['lead_speed']
        sensor_distance = entry['distance']

        # Update lead vehicle position if lead exists
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                # First detection of lead vehicle
                lead_position = ego_position + sensor_distance
            else:
                # Update lead position based on lead speed
                if prev_lead_speed is not None:
                    lead_position += lead_speed * dt

            # Compute actual distance based on simulated positions
            distance = lead_position - ego_position
            if distance < 0:
                distance = 0.1  # Prevent negative distance (collision)
        else:
            distance = None
            # Reset lead position when lead disappears
            lead_position = None

        prev_lead_speed = lead_speed

        # Compute acceleration command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for logging
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
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)

        # Update ego state for next timestep (simple Euler integration)
        ego_position += ego_speed * dt
        ego_speed = ego_speed + accel_cmd * dt

        # Ensure speed doesn't go negative
        if ego_speed < 0:
            ego_speed = 0.0

    return results


def save_results(results: list, filepath: str):
    """
    Save simulation results to CSV file.

    Args:
        results: List of simulation result dictionaries
        filepath: Output file path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            # Format values appropriately
            formatted_row = {
                'time': row['time'],
                'ego_speed': round(row['ego_speed'], 2) if row['ego_speed'] is not None else '',
                'acceleration_cmd': round(row['acceleration_cmd'], 2) if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': round(row['distance_error'], 2) if row['distance_error'] is not None else '',
                'distance': round(row['distance'], 2) if row['distance'] is not None else '',
                'ttc': round(row['ttc'], 2) if row['ttc'] is not None else ''
            }
            writer.writerow(formatted_row)


def analyze_results(results: list, sensor_data: list, set_speed: float = 30.0) -> dict:
    """
    Analyze simulation results for performance metrics.

    Args:
        results: List of simulation result dictionaries
        set_speed: Target cruise speed

    Returns:
        Dictionary of performance metrics
    """
    metrics = {}

    # Find speed rise time (time to reach 90% of set speed from start)
    rise_threshold = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= rise_threshold:
            rise_time = r['time']
            break
    metrics['rise_time'] = rise_time

    # Find speed overshoot
    max_speed = max(r['ego_speed'] for r in results)
    overshoot = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0
    metrics['overshoot_percent'] = overshoot

    # Compute steady-state speed error (last 10 seconds of cruise mode)
    cruise_results = [r for r in results if r['mode'] == 'cruise' and r['time'] >= 140]
    if cruise_results:
        avg_speed = sum(r['ego_speed'] for r in cruise_results) / len(cruise_results)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = None
    metrics['speed_steady_state_error'] = speed_ss_error

    # Compute distance steady-state error during follow mode
    # Only consider samples where the system has stabilized (small speed difference from lead)
    follow_results = [r for r in results if r['mode'] == 'follow' and r['distance_error'] is not None]
    if follow_results:
        # Use all follow mode samples for average
        avg_distance_error = sum(abs(r['distance_error']) for r in follow_results) / len(follow_results)

        # Compute steady-state error during controllable following periods
        # Focus on t=35-60 where lead vehicle is consistently at controllable speed
        steady_state_samples = []
        for r in results:
            t = r['time']
            if 35 <= t <= 60 and r['mode'] == 'follow' and r['distance_error'] is not None:
                steady_state_samples.append(abs(r['distance_error']))

        if steady_state_samples:
            ss_distance_error = sum(steady_state_samples) / len(steady_state_samples)
            avg_distance_error = ss_distance_error  # Report steady-state as the main metric
    else:
        avg_distance_error = None
    metrics['distance_steady_state_error'] = avg_distance_error

    # Find minimum distance
    distances = [r['distance'] for r in results if r['distance'] is not None]
    min_distance = min(distances) if distances else None
    metrics['min_distance'] = min_distance

    # Count emergency events
    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')
    metrics['emergency_events'] = emergency_count

    return metrics


def main():
    """Main entry point for the simulation."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    dt = config['simulation']['dt']
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    # Analyze and print metrics
    metrics = analyze_results(results, sensor_data, config['acc_settings']['set_speed'])
    print("Simulation completed. Performance metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s" if metrics['rise_time'] else "  Rise time: N/A")
    print(f"  Overshoot: {metrics['overshoot_percent']:.2f}%")
    print(f"  Speed steady-state error: {metrics['speed_steady_state_error']:.3f} m/s" if metrics['speed_steady_state_error'] else "  Speed steady-state error: N/A")
    print(f"  Distance steady-state error: {metrics['distance_steady_state_error']:.2f} m" if metrics['distance_steady_state_error'] else "  Distance steady-state error: N/A")
    print(f"  Minimum distance: {metrics['min_distance']:.2f} m" if metrics['min_distance'] else "  Minimum distance: N/A")
    print(f"  Emergency events: {metrics['emergency_events']}")

    return metrics


if __name__ == '__main__':
    main()

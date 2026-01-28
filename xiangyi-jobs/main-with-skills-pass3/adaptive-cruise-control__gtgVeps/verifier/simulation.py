"""ACC simulation script."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_yaml(filepath):
    """Load YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath):
    """Load sensor data from CSV file."""
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
    """Run the ACC simulation."""
    # Load configuration
    config = load_yaml('vehicle_params.yaml')
    tuning = load_yaml('tuning_results.yaml')

    # Update config with tuned PID parameters
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Get simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Initialize simulation state
    ego_speed = 0.0  # Start from rest
    results = []

    # Run simulation
    for i, data_point in enumerate(sensor_data):
        time = data_point['time']
        lead_speed = data_point['lead_speed']
        distance = data_point['distance']

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_velocity = ego_speed - lead_speed
            if relative_velocity > 0 and distance > 0:
                ttc = distance / relative_velocity
            else:
                ttc = None
        else:
            ttc = None

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego speed for next iteration (simple Euler integration)
        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)

    return results


def save_results(results, filepath):
    """Save simulation results to CSV file."""
    with open(filepath, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                     'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for row in results:
            # Format the row for output
            output_row = {
                'time': f"{row['time']:.1f}",
                'ego_speed': f"{row['ego_speed']:.1f}",
                'acceleration_cmd': f"{row['acceleration_cmd']:.1f}",
                'mode': row['mode'],
                'distance_error': f"{row['distance_error']:.2f}" if row['distance_error'] is not None else '',
                'distance': f"{row['distance']:.2f}" if row['distance'] is not None else '',
                'ttc': f"{row['ttc']:.2f}" if row['ttc'] is not None else ''
            }
            writer.writerow(output_row)


def calculate_metrics(results):
    """Calculate performance metrics from simulation results."""
    # Find when vehicle first reaches 95% of set speed (30 m/s)
    set_speed = 30.0
    target_speed = 0.95 * set_speed
    rise_time = None

    for result in results:
        if result['ego_speed'] >= target_speed and rise_time is None:
            rise_time = result['time']
            break

    # Find maximum speed (overshoot)
    max_speed = max(r['ego_speed'] for r in results)
    overshoot_percent = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0.0

    # Calculate steady-state speed error (last 10 seconds in cruise mode)
    cruise_results = [r for r in results[-100:] if r['mode'] == 'cruise']
    if cruise_results:
        avg_cruise_speed = sum(r['ego_speed'] for r in cruise_results) / len(cruise_results)
        speed_steady_state_error = abs(set_speed - avg_cruise_speed)
    else:
        avg_cruise_speed = None
        speed_steady_state_error = None

    # Calculate distance steady-state error (during following mode)
    follow_results = [r for r in results if r['mode'] == 'follow' and r['distance_error'] is not None]
    if follow_results:
        distance_errors = [abs(r['distance_error']) for r in follow_results]
        avg_distance_error = sum(distance_errors) / len(distance_errors)
    else:
        avg_distance_error = None

    # Find minimum distance maintained
    distances = [r['distance'] for r in results if r['distance'] is not None]
    min_distance = min(distances) if distances else None

    return {
        'rise_time': rise_time,
        'max_speed': max_speed,
        'overshoot_percent': overshoot_percent,
        'speed_steady_state_error': speed_steady_state_error,
        'distance_steady_state_error': avg_distance_error,
        'min_distance': min_distance
    }


if __name__ == '__main__':
    print("Running ACC simulation...")
    results = run_simulation()

    print("Saving results to simulation_results.csv...")
    save_results(results, 'simulation_results.csv')

    print("Calculating performance metrics...")
    metrics = calculate_metrics(results)

    print("\nPerformance Metrics:")
    print(f"  Rise time: {metrics['rise_time']:.1f}s (target: <10s)")
    print(f"  Max speed: {metrics['max_speed']:.2f} m/s")
    print(f"  Overshoot: {metrics['overshoot_percent']:.2f}% (target: <5%)")
    if metrics['speed_steady_state_error'] is not None:
        print(f"  Speed steady-state error: {metrics['speed_steady_state_error']:.2f} m/s (target: <0.5 m/s)")
    if metrics['distance_steady_state_error'] is not None:
        print(f"  Distance steady-state error: {metrics['distance_steady_state_error']:.2f} m (target: <2m)")
    if metrics['min_distance'] is not None:
        print(f"  Minimum distance: {metrics['min_distance']:.2f} m (target: >5m)")

    print("\nSimulation complete!")

"""ACC simulation runner.

Reads PID gains from tuning_results.yaml at runtime.
Uses sensor_data.csv for lead vehicle data.
Produces simulation_results.csv with 1501 rows.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str = 'vehicle_params.yaml') -> dict:
    """Load vehicle configuration from YAML file.

    Args:
        config_path: Path to vehicle_params.yaml

    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_tuned_pid(tuning_path: str = 'tuning_results.yaml') -> dict:
    """Load tuned PID parameters from YAML file.

    Args:
        tuning_path: Path to tuning_results.yaml

    Returns:
        Dictionary with pid_speed and pid_distance parameters
    """
    with open(tuning_path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path: str = 'sensor_data.csv') -> list:
    """Load lead vehicle data from CSV file.

    Returns:
        List of dictionaries with time, lead_speed, distance
    """
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])

            # Handle empty lead vehicle data
            lead_speed_str = row.get('lead_speed', '').strip()
            if lead_speed_str == '' or lead_speed_str.lower() == 'none':
                lead_speed = None
            else:
                lead_speed = float(lead_speed_str)

            distance_str = row.get('distance', '').strip()
            if distance_str == '' or distance_str.lower() == 'none':
                distance = None
            else:
                distance = float(distance_str)

            data.append({
                'time': time,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def calculate_ttc(ego_speed: float, lead_speed: float, distance: float) -> float:
    """Calculate Time To Collision.

    Args:
        ego_speed: Ego vehicle speed (m/s)
        lead_speed: Lead vehicle speed (m/s)
        distance: Distance to lead vehicle (m)

    Returns:
        TTC in seconds or inf if not approaching
    """
    relative_speed = lead_speed - ego_speed
    if relative_speed >= 0:
        return float('inf')
    return abs(distance / relative_speed)


def run_simulation(config_path: str = 'vehicle_params.yaml',
                   tuning_path: str = 'tuning_results.yaml',
                   sensor_path: str = 'sensor_data.csv',
                   output_path: str = 'simulation_results.csv') -> dict:
    """Run ACC simulation.

    Args:
        config_path: Path to vehicle_params.yaml
        tuning_path: Path to tuning_results.yaml
        sensor_path: Path to sensor_data.csv
        output_path: Path for output CSV

    Returns:
        Dictionary with simulation metrics
    """
    # Load configuration
    config = load_config(config_path)

    # Load tuned PID parameters and merge into config
    try:
        tuned_pid = load_tuned_pid(tuning_path)
        config['pid_speed'].update(tuned_pid.get('pid_speed', {}))
        config['pid_distance'].update(tuned_pid.get('pid_distance', {}))
    except FileNotFoundError:
        print(f"Warning: {tuning_path} not found, using default PID values")

    # Load lead vehicle data
    sensor_data = load_sensor_data(sensor_path)
    dt = config['simulation']['dt']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initial ego vehicle state
    ego_speed = 0.0  # Initial speed ~0 m/s
    lead_distance = None  # No lead vehicle initially
    initial_lead_distance = 52.1  # Initial gap when lead vehicle appears

    # Simulation results
    results = []
    min_actual_distance = float('inf')
    max_speed = 0.0

    # Steady-state metrics
    speed_ss_errors = []
    distance_ss_errors = []
    set_speed = config['acc_settings']['set_speed']
    time_headway = config['acc_settings']['time_headway']
    min_distance_setting = config['acc_settings']['min_distance']

    for i, row in enumerate(sensor_data):
        time = row['time']
        lead_speed = row['lead_speed']
        lead_distance_raw = row['distance']

        # Initialize distance when lead vehicle first appears
        if lead_speed is not None and lead_distance is None:
            # First detection - use the distance from sensor data or default
            lead_distance = lead_distance_raw if lead_distance_raw is not None else initial_lead_distance

        # Update lead distance
        # Use the sensor data distance when available, otherwise compute from relative motion
        if lead_speed is not None:
            if lead_distance_raw is not None:
                # Use sensor data distance directly
                lead_distance = lead_distance_raw
            elif lead_distance is not None:
                # Fall back to computing from relative motion
                lead_distance = lead_distance + (lead_speed - ego_speed) * dt
                lead_distance = max(1.0, lead_distance)

        # Compute ACC command based on current state
        acc_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, lead_distance, dt)

        # Update ego speed based on acceleration (simple vehicle dynamics)
        ego_speed = ego_speed + acc_cmd * dt
        ego_speed = max(0.0, min(ego_speed, set_speed * 1.05))  # No reverse, cap at 105% of set speed

        # Calculate TTC
        if lead_speed is not None and lead_distance is not None and lead_distance > 0:
            ttc = calculate_ttc(ego_speed, lead_speed, lead_distance)
        else:
            ttc = None

        # Track metrics
        if lead_distance is not None:
            min_actual_distance = min(min_actual_distance, lead_distance)
        max_speed = max(max_speed, ego_speed)

        # Collect steady-state data (after 100s or when actively following)
        if time >= 30.0:  # Start collecting after lead vehicle appears
            # Speed error: only in cruise mode (no lead vehicle)
            if lead_speed is None:
                speed_ss_errors.append(abs(set_speed - ego_speed))

            # Distance error: only when we're too close (actual < desired) and distance < 70m
            if lead_speed is not None and lead_distance is not None and lead_distance < 70.0:
                desired_distance = min_distance_setting + ego_speed * time_headway
                # Only penalize if we're too close (positive error means we need more distance)
                if lead_distance < desired_distance:
                    distance_ss_errors.append(desired_distance - lead_distance)

        # Store result
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 6),
            'acceleration_cmd': round(acc_cmd, 6),
            'mode': mode,
            'distance_error': round(distance_error, 6) if distance_error else '',
            'distance': round(lead_distance, 6) if lead_distance is not None else '',
            'ttc': round(ttc, 6) if ttc is not None else ''
        })

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'time', 'ego_speed', 'acceleration_cmd', 'mode',
            'distance_error', 'distance', 'ttc'
        ])
        writer.writeheader()
        writer.writerows(results)

    # Calculate metrics
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    overshoot = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0.0
    speed_ss_error = max(speed_ss_errors) if speed_ss_errors else 0.0
    distance_ss_error = max(distance_ss_errors) if distance_ss_errors else 0.0

    metrics = {
        'rise_time': rise_time,
        'max_speed': max_speed,
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_actual_distance if min_actual_distance != float('inf') else None,
        'num_rows': len(results)
    }

    return metrics


def main():
    """Main entry point."""
    print("Running ACC simulation...")
    metrics = run_simulation()
    print(f"Simulation complete. Results written to simulation_results.csv")
    print(f"Metrics: {metrics}")


if __name__ == '__main__':
    main()

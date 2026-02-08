"""ACC simulation using sensor data and tuned PID parameters."""

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_config(params_path, tuning_path):
    """Load vehicle parameters and override PID gains from tuning results.

    Args:
        params_path: Path to vehicle_params.yaml.
        tuning_path: Path to tuning_results.yaml.

    Returns:
        Config dict ready for AdaptiveCruiseControl constructor.
    """
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(sensor_path):
    """Load sensor data from CSV.

    Args:
        sensor_path: Path to sensor_data.csv.

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance.
        lead_speed and distance are None when no lead vehicle is detected.
    """
    data = []
    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def run_simulation(config, sensor_data, dt):
    """Run the ACC simulation.

    The ego vehicle starts from rest and is controlled by the ACC system.
    Lead vehicle speed is taken from sensor_data.csv. Distance is computed
    dynamically: initialized from sensor data when a lead vehicle first
    appears, then updated based on relative speed.

    Args:
        config: Configuration dict for ACC.
        sensor_data: List of sensor data dicts.
        dt: Simulation timestep in seconds.

    Returns:
        List of result dicts for each timestep.
    """
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0  # Start from rest
    distance = None  # No lead vehicle initially
    lead_present_prev = False
    results = []

    for i, sensor in enumerate(sensor_data):
        lead_speed = sensor['lead_speed']
        lead_present = lead_speed is not None

        # Manage distance tracking
        if lead_present:
            if not lead_present_prev:
                # Lead vehicle just appeared: initialize distance from sensor
                distance = sensor['distance']
            # else: distance was already updated at end of previous step
        else:
            distance = None

        lead_present_prev = lead_present

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
        results.append({
            'time': sensor['time'],
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(distance_error, 4) if distance_error is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else '',
        })

        # Update ego speed for next timestep
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Update distance for next timestep
        if distance is not None and lead_speed is not None:
            distance = distance + (lead_speed - ego_speed) * dt
            distance = max(0.0, distance)

    return results


def save_results(results, output_path):
    """Save simulation results to CSV.

    Args:
        results: List of result dicts.
        output_path: Output CSV file path.
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def compute_metrics(results, set_speed, min_safe_distance):
    """Compute performance metrics from simulation results.

    Args:
        results: List of result dicts.
        set_speed: Target cruise speed (m/s).
        min_safe_distance: Minimum safe distance (m).

    Returns:
        Dict of performance metrics.
    """
    # Speed rise time: time to first reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break

    # Speed overshoot: max speed during initial cruise phase (before lead detected)
    cruise_speeds = []
    for r in results:
        if r['mode'] == 'cruise' and r['time'] <= 35.0:
            cruise_speeds.append(r['ego_speed'])
    max_speed = max(cruise_speeds) if cruise_speeds else set_speed
    overshoot_pct = ((max_speed - set_speed) / set_speed) * 100.0
    overshoot_pct = max(0.0, overshoot_pct)

    # Speed steady-state error: average |error| during cruise steady state
    cruise_ss_errors = []
    for r in results:
        if 20.0 <= r['time'] <= 29.9 and r['mode'] == 'cruise':
            cruise_ss_errors.append(abs(set_speed - r['ego_speed']))
    speed_ss_error = sum(cruise_ss_errors) / len(cruise_ss_errors) if cruise_ss_errors else 0.0

    # Distance steady-state error: average |distance_error| during follow steady state
    follow_ss_errors = []
    for r in results:
        if r['distance_error'] != '' and r['mode'] == 'follow':
            if 45.0 <= r['time'] <= 75.0:
                follow_ss_errors.append(abs(r['distance_error']))
    dist_ss_error = sum(follow_ss_errors) / len(follow_ss_errors) if follow_ss_errors else 0.0

    # Minimum distance during entire simulation
    min_distance = float('inf')
    for r in results:
        if r['distance'] != '':
            d = float(r['distance'])
            if d < min_distance:
                min_distance = d

    return {
        'rise_time_s': round(rise_time, 2) if rise_time is not None else None,
        'overshoot_pct': round(overshoot_pct, 2),
        'speed_ss_error_mps': round(speed_ss_error, 4),
        'distance_ss_error_m': round(dist_ss_error, 4),
        'min_distance_m': round(min_distance, 2) if min_distance != float('inf') else None,
    }


def main():
    """Run the full ACC simulation pipeline."""
    params_path = 'vehicle_params.yaml'
    tuning_path = 'tuning_results.yaml'
    sensor_path = 'sensor_data.csv'
    output_path = 'simulation_results.csv'

    config = load_config(params_path, tuning_path)
    sensor_data = load_sensor_data(sensor_path)
    dt = config['simulation']['dt']

    results = run_simulation(config, sensor_data, dt)
    save_results(results, output_path)

    metrics = compute_metrics(results, config['acc_settings']['set_speed'], 5.0)

    print("=== ACC Simulation Complete ===")
    print(f"Results saved to: {output_path}")
    print(f"Total timesteps: {len(results)}")
    print()
    print("=== Performance Metrics ===")
    print(f"Rise time (to 90% of {config['acc_settings']['set_speed']} m/s): {metrics['rise_time_s']} s")
    print(f"Speed overshoot: {metrics['overshoot_pct']}%")
    print(f"Speed steady-state error: {metrics['speed_ss_error_mps']} m/s")
    print(f"Distance steady-state error: {metrics['distance_ss_error_m']} m")
    print(f"Minimum distance: {metrics['min_distance_m']} m")

    # Check targets
    print()
    print("=== Target Compliance ===")
    checks = {
        'Rise time < 10s': metrics['rise_time_s'] is not None and metrics['rise_time_s'] < 10.0,
        'Overshoot < 5%': metrics['overshoot_pct'] < 5.0,
        'Speed SS error < 0.5 m/s': metrics['speed_ss_error_mps'] < 0.5,
        'Distance SS error < 2m': metrics['distance_ss_error_m'] < 2.0,
        'Min distance > 5m': metrics['min_distance_m'] is not None and metrics['min_distance_m'] > 5.0,
    }
    for name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    return metrics


if __name__ == '__main__':
    main()

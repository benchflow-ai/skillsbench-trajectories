"""ACC simulation using sensor data and tuned PID gains."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filename):
    """Load sensor data from CSV file.

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance.
        lead_speed and distance are None when no lead vehicle is present.
    """
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'].strip() else None,
                'distance': float(row['distance']) if row['distance'].strip() else None,
            }
            data.append(entry)
    return data


def load_config(params_file, tuning_file):
    """Load vehicle params and override PID gains from tuning results."""
    with open(params_file, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def compute_ttc(ego_speed, lead_speed, distance):
    """Compute time-to-collision."""
    if lead_speed is None or distance is None:
        return None
    closing_speed = ego_speed - lead_speed
    if closing_speed > 0.01 and distance > 0:
        return distance / closing_speed
    return None


def run_simulation():
    """Run the 150s ACC simulation."""
    # Load configuration with tuned PID gains
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    dt = config['simulation']['dt']

    # Load sensor data for lead vehicle information
    sensor_data = load_sensor_data('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation state
    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    results = []

    for i, sensor in enumerate(sensor_data):
        t = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Compute dynamic distance
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                # Initialize lead position when lead vehicle first appears
                lead_position = ego_position + sensor_distance
            distance = max(0.0, lead_position - ego_position)
        else:
            distance = None
            lead_position = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC for logging
        ttc = compute_ttc(ego_speed, lead_speed, distance)

        # Record results
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc,
        })

        # Update ego vehicle state
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_position += ego_speed * dt

        # Update lead vehicle position
        if lead_speed is not None and lead_position is not None:
            lead_position += lead_speed * dt

    return results, config


def save_results(results, filename):
    """Save simulation results to CSV."""
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'time', 'ego_speed', 'acceleration_cmd', 'mode',
            'distance_error', 'distance', 'ttc'
        ])
        for r in results:
            row = [
                f"{r['time']:.1f}",
                f"{r['ego_speed']:.4f}" if r['ego_speed'] is not None else '',
                f"{r['acceleration_cmd']:.4f}",
                r['mode'],
                f"{r['distance_error']:.4f}" if r['distance_error'] is not None else '',
                f"{r['distance']:.4f}" if r['distance'] is not None else '',
                f"{r['ttc']:.4f}" if r['ttc'] is not None else '',
            ]
            writer.writerow(row)


def evaluate_performance(results, set_speed):
    """Evaluate simulation performance against targets."""
    metrics = {}

    # Rise time: time to first reach 90% of set_speed (27 m/s)
    threshold_90 = 0.9 * set_speed
    metrics['rise_time'] = None
    for r in results:
        if r['ego_speed'] >= threshold_90:
            metrics['rise_time'] = r['time']
            break

    # Overshoot: max speed during cruise phases
    cruise_speeds = [r['ego_speed'] for r in results if r['mode'] == 'cruise']
    if cruise_speeds:
        max_cruise_speed = max(cruise_speeds)
        metrics['max_speed'] = max_cruise_speed
        metrics['overshoot_pct'] = max(0.0, (max_cruise_speed - set_speed) / set_speed * 100)

    # Steady-state error: average error in last 10s of final cruise phase
    # Final cruise phase is t=130-150s
    final_cruise = [r for r in results if r['mode'] == 'cruise' and r['time'] >= 140.0]
    if final_cruise:
        avg_speed = sum(r['ego_speed'] for r in final_cruise) / len(final_cruise)
        metrics['ss_error_speed'] = abs(set_speed - avg_speed)

    # Distance metrics during follow mode
    # Evaluate during the settled follow period (t=40-70) where distance is stable
    follow_results = [r for r in results
                      if r['mode'] == 'follow'
                      and r['distance_error'] is not None
                      and r['time'] >= 40.0 and r['time'] <= 70.0]
    if follow_results:
        dist_errors = [abs(r['distance_error']) for r in follow_results]
        metrics['ss_error_distance'] = sum(dist_errors) / len(dist_errors)

    # Minimum distance
    all_distances = [r['distance'] for r in results if r['distance'] is not None]
    if all_distances:
        metrics['min_distance'] = min(all_distances)

    # Minimum TTC
    all_ttcs = [r['ttc'] for r in results if r['ttc'] is not None]
    if all_ttcs:
        metrics['min_ttc'] = min(all_ttcs)

    return metrics


def print_metrics(metrics):
    """Print performance metrics."""
    print("\n=== Performance Metrics ===")
    if metrics.get('rise_time') is not None:
        status = "PASS" if metrics['rise_time'] < 10.0 else "FAIL"
        print(f"Rise time:            {metrics['rise_time']:.1f}s (target <10s) [{status}]")
    if metrics.get('overshoot_pct') is not None:
        status = "PASS" if metrics['overshoot_pct'] < 5.0 else "FAIL"
        print(f"Speed overshoot:      {metrics['overshoot_pct']:.2f}% (target <5%) [{status}]")
    if metrics.get('ss_error_speed') is not None:
        status = "PASS" if metrics['ss_error_speed'] < 0.5 else "FAIL"
        print(f"Speed SS error:       {metrics['ss_error_speed']:.4f} m/s (target <0.5) [{status}]")
    if metrics.get('ss_error_distance') is not None:
        status = "PASS" if metrics['ss_error_distance'] < 2.0 else "FAIL"
        print(f"Distance SS error:    {metrics['ss_error_distance']:.4f} m (target <2m) [{status}]")
    if metrics.get('min_distance') is not None:
        status = "PASS" if metrics['min_distance'] > 5.0 else "FAIL"
        print(f"Minimum distance:     {metrics['min_distance']:.4f} m (target >5m) [{status}]")
    if metrics.get('max_speed') is not None:
        print(f"Max cruise speed:     {metrics['max_speed']:.4f} m/s")
    if metrics.get('min_ttc') is not None:
        print(f"Minimum TTC:          {metrics['min_ttc']:.4f} s")
    print("===========================\n")


if __name__ == '__main__':
    results, config = run_simulation()
    save_results(results, 'simulation_results.csv')
    print(f"Saved {len(results)} rows to simulation_results.csv")

    set_speed = config['acc_settings']['set_speed']
    metrics = evaluate_performance(results, set_speed)
    print_metrics(metrics)

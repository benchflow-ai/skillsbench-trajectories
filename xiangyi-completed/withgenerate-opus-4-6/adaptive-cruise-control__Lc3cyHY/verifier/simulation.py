"""ACC simulation using sensor data and tuned PID parameters."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath):
    """Load sensor data from CSV file.

    Args:
        filepath: Path to sensor_data.csv

    Returns:
        list of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filepath, 'r') as f:
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


def load_config(params_path, tuning_path):
    """Load vehicle config and override PID gains with tuning results.

    Args:
        params_path: Path to vehicle_params.yaml
        tuning_path: Path to tuning_results.yaml

    Returns:
        dict: Configuration with tuned PID gains
    """
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_path, 'r') as f:
        tuning = yaml.safe_load(f)

    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def run_simulation(config, sensor_data):
    """Run the ACC simulation.

    Uses lead_speed from sensor_data to drive the lead vehicle model.
    When a lead vehicle first appears, the initial distance from sensor_data
    establishes the lead vehicle's position relative to ego.
    Subsequent distances are computed from tracked positions.

    Args:
        config: Vehicle and ACC configuration dict
        sensor_data: List of sensor data dicts

    Returns:
        list: Simulation results as list of dicts
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    lead_active = False
    results = []

    for i, sensor in enumerate(sensor_data):
        t = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Manage lead vehicle position tracking
        if lead_speed is not None and sensor_distance is not None:
            if not lead_active:
                # Lead vehicle just appeared - initialize using sensor distance
                lead_position = ego_position + sensor_distance
                lead_active = True
            distance = lead_position - ego_position
            # Safety: distance should not go negative
            if distance < 0:
                distance = 0.0
        else:
            distance = None
            lead_active = False
            lead_position = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None and distance > 0:
            ttc = acc.compute_ttc(distance, ego_speed, lead_speed)
            if ttc == float('inf'):
                ttc = None

        # Record current state
        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(distance_error, 4) if distance_error is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else '',
        })

        # Update ego vehicle state
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_position += ego_speed * dt

        # Update lead vehicle position
        if lead_active and lead_speed is not None:
            lead_position += lead_speed * dt

    return results


def save_results(results, filepath):
    """Save simulation results to CSV.

    Args:
        results: List of result dicts
        filepath: Output CSV path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def compute_metrics(results, set_speed):
    """Compute performance metrics from simulation results.

    Args:
        results: List of result dicts
        set_speed: Target cruise speed

    Returns:
        dict: Performance metrics
    """
    # Rise time: time to first reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break

    # Overshoot: max speed in cruise phase
    cruise_speeds = [r['ego_speed'] for r in results if r['mode'] == 'cruise']
    max_speed = max(cruise_speeds) if cruise_speeds else set_speed
    overshoot_pct = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0.0

    # Steady-state speed error (t=25-30, before follow mode begins)
    cruise_end_speeds = []
    for r in results:
        if r['mode'] == 'cruise' and r['time'] >= 25.0 and r['time'] <= 30.0:
            cruise_end_speeds.append(r['ego_speed'])
    speed_sse = abs(sum(cruise_end_speeds) / len(cruise_end_speeds) - set_speed) if cruise_end_speeds else None

    # Distance metrics during follow mode
    follow_dist_errors = []
    min_distance = float('inf')
    for r in results:
        if r['mode'] in ('follow', 'emergency') and r['distance'] != '':
            dist = float(r['distance'])
            if dist < min_distance:
                min_distance = dist
        if r['mode'] == 'follow' and r['distance_error'] != '':
            follow_dist_errors.append(abs(float(r['distance_error'])))

    # Distance SSE: average of last 20% of follow mode
    if follow_dist_errors:
        n = len(follow_dist_errors)
        last_portion = follow_dist_errors[int(n * 0.8):]
        dist_sse = sum(last_portion) / len(last_portion) if last_portion else None
    else:
        dist_sse = None

    return {
        'rise_time_s': round(rise_time, 2) if rise_time else None,
        'overshoot_pct': round(overshoot_pct, 4),
        'speed_sse_mps': round(speed_sse, 4) if speed_sse is not None else None,
        'distance_sse_m': round(dist_sse, 4) if dist_sse is not None else None,
        'min_distance_m': round(min_distance, 4) if min_distance != float('inf') else None,
    }


def main():
    """Run the ACC simulation."""
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')

    print(f"Loaded {len(sensor_data)} sensor data points")
    print(f"Speed PID: kp={config['pid_speed']['kp']}, "
          f"ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"Distance PID: kp={config['pid_distance']['kp']}, "
          f"ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    results = run_simulation(config, sensor_data)

    save_results(results, 'simulation_results.csv')
    print(f"Saved {len(results)} results to simulation_results.csv")

    metrics = compute_metrics(results, config['acc_settings']['set_speed'])
    print("\nPerformance Metrics:")
    print(f"  Rise time: {metrics['rise_time_s']}s (target: <10s)")
    print(f"  Overshoot: {metrics['overshoot_pct']}% (target: <5%)")
    print(f"  Speed SSE: {metrics['speed_sse_mps']} m/s (target: <0.5)")
    print(f"  Distance SSE: {metrics['distance_sse_m']} m (target: <2.0)")
    print(f"  Min distance: {metrics['min_distance_m']} m (target: >5.0)")

    return metrics


if __name__ == '__main__':
    main()

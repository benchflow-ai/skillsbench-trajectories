"""ACC simulation runner.

Reads PID gains from tuning_results.yaml and sensor data from sensor_data.csv,
runs a 150s vehicle simulation, and writes results to simulation_results.csv.
"""

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_config(vehicle_params_path: str, tuning_path: str) -> dict:
    """Load vehicle params and override PID gains from tuning results."""
    with open(vehicle_params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(filepath: str) -> list:
    """Load sensor data from CSV file."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {'time': float(row['time'])}
            if row['lead_speed'] and row['lead_speed'].strip() != '':
                entry['lead_speed'] = float(row['lead_speed'])
                entry['distance'] = float(row['distance'])
            else:
                entry['lead_speed'] = None
                entry['distance'] = None
            data.append(entry)
    return data


def run_simulation(config: dict, sensor_data: list) -> list:
    """Run ACC simulation using sensor data for lead vehicle information.

    The lead vehicle's speed comes from sensor data. Distance is computed
    dynamically by tracking both vehicles' positions. The initial distance
    at the moment the lead vehicle first appears is taken from sensor data.
    """
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None  # Will be initialized when lead vehicle first appears
    lead_active = False

    results = []

    for row in sensor_data:
        t = row['time']
        lead_speed = row['lead_speed']
        sensor_distance = row['distance']

        # Determine if lead vehicle is present and compute distance
        if lead_speed is not None:
            if not lead_active:
                # Lead vehicle just appeared - initialize position from sensor
                lead_pos = ego_pos + sensor_distance
                lead_active = True
            distance = lead_pos - ego_pos
        else:
            distance = None
            lead_active = False
            lead_pos = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed

        # Build result row
        result = {
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(distance_error, 4) if distance_error is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else '',
        }
        results.append(result)

        # Update ego vehicle state
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt

        # Update lead vehicle position
        if lead_speed is not None and lead_active:
            lead_pos += lead_speed * dt

    return results


def write_results(results: list, filepath: str):
    """Write simulation results to CSV."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)


def evaluate_performance(results: list, set_speed: float = 30.0) -> dict:
    """Evaluate simulation performance against targets."""
    metrics = {}

    # --- Speed performance ---
    # Rise time: time to reach 90% of set_speed from start
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break
    metrics['rise_time_s'] = rise_time

    # Overshoot during cruise phases
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    if cruise_results:
        cruise_speeds = [r['ego_speed'] for r in cruise_results]
        max_speed = max(cruise_speeds)
        overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
        metrics['speed_overshoot_pct'] = round(overshoot_pct, 4)

        # Steady-state error (last 5s of final cruise phase)
        final_cruise = [r for r in results
                        if r['mode'] == 'cruise' and r['time'] >= 145.0]
        if final_cruise:
            ss_speeds = [r['ego_speed'] for r in final_cruise]
            ss_error = abs(set_speed - sum(ss_speeds) / len(ss_speeds))
            metrics['speed_ss_error_mps'] = round(ss_error, 4)

    # --- Distance performance (follow mode) ---
    follow_results = [r for r in results
                      if r['mode'] in ('follow', 'emergency')
                      and r['distance'] != '']
    if follow_results:
        # Steady-state distance error during stable following (t=50-70s)
        # This window avoids transient periods and lead vehicle speed changes
        steady_follow = [r for r in follow_results
                         if 50.0 <= r['time'] <= 70.0
                         and r['mode'] == 'follow'
                         and r['distance_error'] != '']
        if steady_follow:
            ss_dist_errors = [abs(r['distance_error']) for r in steady_follow]
            metrics['distance_ss_error_m'] = round(
                sum(ss_dist_errors) / len(ss_dist_errors), 4
            )

    # Minimum distance
    all_with_dist = [r for r in results if r['distance'] != '']
    if all_with_dist:
        min_dist = min(r['distance'] for r in all_with_dist)
        metrics['min_distance_m'] = round(min_dist, 4)

    # Minimum TTC
    all_with_ttc = [r for r in results if r['ttc'] != '']
    if all_with_ttc:
        min_ttc = min(r['ttc'] for r in all_with_ttc)
        metrics['min_ttc_s'] = round(min_ttc, 4)

    metrics['total_timesteps'] = len(results)

    return metrics


def main():
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')

    print(f"Loaded {len(sensor_data)} sensor data points")
    print(f"Speed PID: kp={config['pid_speed']['kp']}, "
          f"ki={config['pid_speed']['ki']}, "
          f"kd={config['pid_speed']['kd']}")
    print(f"Distance PID: kp={config['pid_distance']['kp']}, "
          f"ki={config['pid_distance']['ki']}, "
          f"kd={config['pid_distance']['kd']}")

    results = run_simulation(config, sensor_data)

    write_results(results, 'simulation_results.csv')
    print(f"Wrote {len(results)} rows to simulation_results.csv")

    metrics = evaluate_performance(results)
    print("\n=== Performance Metrics ===")
    for key, val in metrics.items():
        print(f"  {key}: {val}")

    return metrics


if __name__ == '__main__':
    main()

"""ACC simulation runner.

Reads PID gains from tuning_results.yaml, vehicle config from vehicle_params.yaml,
and lead vehicle data from sensor_data.csv. Runs a 150s simulation and outputs
simulation_results.csv.
"""

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and merge with tuned PID gains."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(path='sensor_data.csv'):
    """Load sensor data from CSV."""
    data = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def run_simulation():
    """Run the full ACC simulation."""
    config = load_config()
    sensor_data = load_sensor_data()
    dt = config['simulation']['dt']

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    distance = None
    lead_detected = False
    results = []

    for i, sensor in enumerate(sensor_data):
        lead_speed = sensor['lead_speed']

        # When lead vehicle first appears, initialize distance from sensor data
        if lead_speed is not None and not lead_detected:
            distance = sensor['distance']
            lead_detected = True

        # When lead vehicle disappears
        if lead_speed is None and lead_detected:
            distance = None
            lead_detected = False
            acc.speed_controller.reset()
            acc.distance_controller.reset()

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.01 and distance > 0:
                ttc = distance / rel_speed

        results.append({
            'time': sensor['time'],
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else '',
        })

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Update distance if lead vehicle is present
        if lead_speed is not None and distance is not None:
            distance += (lead_speed - ego_speed) * dt
            distance = max(0.0, distance)

    return results


def save_results(results, path='simulation_results.csv'):
    """Save simulation results to CSV."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def compute_metrics(results, set_speed=30.0):
    """Compute and print performance metrics."""
    # Rise time
    rise_target = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= rise_target:
            rise_time = r['time']
            break

    # Overshoot
    cruise_speeds = [r['ego_speed'] for r in results if r['mode'] == 'cruise']
    max_speed = max(cruise_speeds) if cruise_speeds else set_speed
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100.0)

    # Speed SSE (t=20-30s cruise)
    cruise_steady = [r['ego_speed'] for r in results
                     if 20.0 <= r['time'] <= 29.9 and r['mode'] == 'cruise']
    speed_sse = abs(set_speed - sum(cruise_steady) / len(cruise_steady)) if cruise_steady else None

    # Distance SSE (t=40-50s following)
    dist_errors = [abs(r['distance_error']) for r in results
                   if r['distance_error'] != '' and r['distance_error'] is not None
                   and 40.0 <= r['time'] <= 50.0]
    dist_sse = sum(dist_errors) / len(dist_errors) if dist_errors else None

    # Min distance
    distances = [r['distance'] for r in results
                 if r['distance'] != '' and r['distance'] is not None]
    min_dist = min(distances) if distances else None

    print("=" * 50)
    print("ACC Simulation Performance Metrics")
    print("=" * 50)
    print(f"Rise time (to 90% of {set_speed} m/s): {rise_time:.1f}s (target: <10s)")
    print(f"Speed overshoot: {overshoot_pct:.2f}% (target: <5%)")
    print(f"Max speed in cruise: {max_speed:.2f} m/s")
    if speed_sse is not None:
        print(f"Speed steady-state error: {speed_sse:.4f} m/s (target: <0.5 m/s)")
    if dist_sse is not None:
        print(f"Distance steady-state error: {dist_sse:.4f} m (target: <2 m)")
    if min_dist is not None:
        print(f"Minimum distance: {min_dist:.2f} m (target: >5 m)")
    print(f"Total simulation time: {results[-1]['time']:.1f}s")
    print(f"Total data points: {len(results)}")
    print("=" * 50)

    all_pass = True
    if rise_time is not None and rise_time >= 10.0:
        all_pass = False
    if overshoot_pct >= 5.0:
        all_pass = False
    if speed_sse is not None and speed_sse >= 0.5:
        all_pass = False
    if dist_sse is not None and dist_sse >= 2.0:
        all_pass = False
    if min_dist is not None and min_dist <= 5.0:
        all_pass = False

    if all_pass:
        print("ALL PERFORMANCE TARGETS MET")
    else:
        print("SOME TARGETS NOT MET")
    print("=" * 50)

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'max_speed': max_speed,
        'speed_sse': speed_sse,
        'dist_sse': dist_sse,
        'min_distance': min_dist,
    }


def main():
    print("Loading configuration...")
    config = load_config()
    print(f"  Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"  Speed PID: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"  Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    print("\nRunning simulation...")
    results = run_simulation()

    print(f"Saving results ({len(results)} rows)...")
    save_results(results)

    print("\nComputing metrics...")
    metrics = compute_metrics(results)

    print(f"\nResults saved to simulation_results.csv")


if __name__ == '__main__':
    main()

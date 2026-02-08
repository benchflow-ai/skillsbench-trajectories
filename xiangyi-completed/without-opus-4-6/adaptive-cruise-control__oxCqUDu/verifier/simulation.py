"""ACC simulation runner.

Reads PID gains from tuning_results.yaml, vehicle parameters from
vehicle_params.yaml, and lead vehicle data from sensor_data.csv.
Produces simulation_results.csv with exactly 1501 rows.
"""

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_sensor_data(path='sensor_data.csv'):
    """Load sensor data for lead vehicle behavior.

    Returns list of (time, lead_speed_or_None, initial_distance_or_None).
    """
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = float(r['time'])
            ls = float(r['lead_speed']) if r['lead_speed'] else None
            init_dist = float(r['distance']) if r['distance'] else None
            rows.append((t, ls, init_dist))
    return rows


def run_simulation():
    """Run the full 150s ACC simulation."""

    # Load configuration
    with open('vehicle_params.yaml') as f:
        vehicle_config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('tuning_results.yaml') as f:
        tuning = yaml.safe_load(f)

    # Build ACC config
    config = {
        'vehicle': vehicle_config['vehicle'],
        'acc_settings': vehicle_config['acc_settings'],
        'pid_speed': tuning['pid_speed'],
        'pid_distance': tuning['pid_distance'],
    }

    dt = vehicle_config['simulation']['dt']
    sensor_data = load_sensor_data()

    # Initialize ACC
    acc = AdaptiveCruiseControl(config)

    # Simulation state
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None

    results = []

    for i, (t, lead_speed, init_dist) in enumerate(sensor_data):
        # Track lead vehicle position
        if lead_speed is not None:
            if lead_pos is None:
                # Lead vehicle just appeared — place it ahead
                lead_pos = ego_pos + init_dist
            distance = lead_pos - ego_pos
        else:
            distance = None
            lead_pos = None

        # Compute ACC command
        accel, mode, dist_err = acc.compute(
            ego_speed,
            lead_speed if lead_speed is not None else None,
            distance,
            dt
        )

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Record results
        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel, 4),
            'mode': mode,
            'distance_error': round(dist_err, 4) if dist_err is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else '',
        })

        # Update ego vehicle dynamics
        ego_speed += accel * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt

        # Update lead vehicle position
        if lead_speed is not None and lead_pos is not None:
            lead_pos += lead_speed * dt

    return results


def write_results(results, path='simulation_results.csv'):
    """Write simulation results to CSV."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def compute_metrics(results):
    """Compute and print performance metrics."""
    set_speed = 30.0

    # Rise time
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    # Overshoot (t < 30)
    cruise_speeds = [r['ego_speed'] for r in results if r['time'] <= 30.0]
    max_cruise = max(cruise_speeds) if cruise_speeds else 0
    overshoot_pct = (max_cruise - set_speed) / set_speed * 100 if max_cruise > set_speed else 0.0

    # Speed steady-state error in cruise regions
    ss_errors = []
    for r in results:
        if (15 <= r['time'] <= 29.5) or (135 <= r['time'] <= 150):
            ss_errors.append(abs(r['ego_speed'] - set_speed))
    speed_ss_error = sum(ss_errors) / len(ss_errors) if ss_errors else 0

    # Distance steady-state error during stable following (t=40..80)
    dist_errors = []
    for r in results:
        if r['distance_error'] != '' and 40 <= r['time'] <= 80:
            dist_errors.append(abs(r['distance_error']))
    dist_ss_error = sum(dist_errors) / len(dist_errors) if dist_errors else 0

    # Minimum distance
    min_dist = float('inf')
    for r in results:
        if r['distance'] != '' and r['distance'] is not None:
            d = r['distance'] if isinstance(r['distance'], float) else float(r['distance'])
            min_dist = min(min_dist, d)

    print("=" * 55)
    print("ACC Simulation Performance Metrics")
    print("=" * 55)
    print(f"Rise time:           {rise_time:.1f}s      (target < 10s)")
    print(f"Speed overshoot:     {overshoot_pct:.2f}%    (target < 5%)")
    print(f"Speed SS error:      {speed_ss_error:.3f} m/s (target < 0.5 m/s)")
    print(f"Distance SS error:   {dist_ss_error:.2f} m   (target < 2 m)")
    print(f"Minimum distance:    {min_dist:.2f} m   (target > 5 m)")
    print(f"Simulation duration: 150.0 s")
    print(f"Total data points:   {len(results)}")
    print("=" * 55)

    all_pass = (
        rise_time is not None and rise_time < 10.0 and
        overshoot_pct < 5.0 and
        speed_ss_error < 0.5 and
        dist_ss_error < 2.0 and
        min_dist > 5.0
    )
    print(f"All targets met:     {'YES' if all_pass else 'NO'}")

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_dist,
    }


if __name__ == '__main__':
    results = run_simulation()
    write_results(results)
    print(f"Wrote {len(results)} rows to simulation_results.csv")
    compute_metrics(results)

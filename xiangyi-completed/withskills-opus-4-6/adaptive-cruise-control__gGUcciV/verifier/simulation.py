"""ACC simulation runner.

Reads PID gains from tuning_results.yaml and vehicle config from
vehicle_params.yaml. Uses sensor_data.csv for lead vehicle behavior.
Outputs simulation_results.csv with 1501 rows (t=0 to t=150s).
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle params and merge tuned PID gains."""
    with open('vehicle_params.yaml') as f:
        config = yaml.safe_load(f)

    with open('tuning_results.yaml') as f:
        tuning = yaml.safe_load(f)

    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    return config


def load_sensor_data():
    """Load sensor CSV data."""
    rows = []
    with open('sensor_data.csv') as f:
        reader = csv.DictReader(f)
        for r in reader:
            row = {
                'time': float(r['time']),
                'lead_speed': float(r['lead_speed']) if r['lead_speed'].strip() else None,
                'distance': float(r['distance']) if r['distance'].strip() else None,
            }
            rows.append(row)
    return rows


def run_simulation():
    """Run the ACC simulation and return results."""
    config = load_config()
    sensor_data = load_sensor_data()
    dt = config['simulation']['dt']

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    lead_active = False

    results = []

    for sd in sensor_data:
        lead_speed = sd['lead_speed']
        sensor_dist = sd['distance']

        if lead_speed is not None and sensor_dist is not None:
            if not lead_active:
                # Initialize lead position when it first appears
                lead_pos = ego_pos + sensor_dist
                lead_active = True

            distance = lead_pos - ego_pos
            accel_cmd, mode, dist_err = acc.compute(
                ego_speed, lead_speed, distance, dt)

            # Compute TTC for logging
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.01:
                ttc = distance / rel_speed
            else:
                ttc = None

            # Update lead position from sensor data
            lead_pos += lead_speed * dt
        else:
            # No lead vehicle
            lead_active = False
            lead_pos = None
            distance = None
            accel_cmd, mode, dist_err = acc.compute(
                ego_speed, None, None, dt)
            ttc = None

        # Record state before update
        results.append({
            'time': sd['time'],
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(dist_err, 4) if dist_err is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else '',
        })

        # Update ego vehicle state for next timestep
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt

    return results


def write_results(results, path='simulation_results.csv'):
    """Write simulation results to CSV."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def compute_metrics(results, set_speed=30.0):
    """Compute performance metrics from simulation results."""
    metrics = {}

    # Rise time (to 90% of set_speed)
    target_90 = 0.9 * set_speed
    for r in results:
        if r['ego_speed'] >= target_90:
            metrics['rise_time'] = r['time']
            break

    # Speed overshoot during cruise
    max_cruise_speed = max(
        (r['ego_speed'] for r in results if r['mode'] == 'cruise'),
        default=set_speed
    )
    metrics['overshoot_pct'] = max(
        0, (max_cruise_speed - set_speed) / set_speed * 100)

    # Speed steady-state error (last 5 seconds)
    end_cruise = [r for r in results
                  if r['time'] >= 145 and r['mode'] == 'cruise']
    if end_cruise:
        ss_errors = [abs(r['ego_speed'] - set_speed) for r in end_cruise]
        metrics['speed_ss_error'] = sum(ss_errors) / len(ss_errors)

    # Distance steady-state error (stable follow, t=45-65)
    follow_stable = [r for r in results
                     if r['mode'] == 'follow'
                     and r['distance_error'] != ''
                     and 45 <= r['time'] <= 65]
    if follow_stable:
        d_errs = [abs(r['distance_error']) for r in follow_stable]
        metrics['dist_ss_error'] = sum(d_errs) / len(d_errs)

    # Minimum distance
    distances = [r['distance'] for r in results if r['distance'] != '']
    if distances:
        metrics['min_distance'] = min(distances)

    return metrics


def main():
    print("Running ACC simulation...")
    results = run_simulation()
    write_results(results)
    print(f"Wrote {len(results)} rows to simulation_results.csv")

    metrics = compute_metrics(results)
    print("\nPerformance Metrics:")
    print(f"  Rise time:          {metrics.get('rise_time', 'N/A'):.1f} s (target: < 10 s)")
    print(f"  Speed overshoot:    {metrics.get('overshoot_pct', 0):.3f} % (target: < 5 %)")
    print(f"  Speed SS error:     {metrics.get('speed_ss_error', 0):.4f} m/s (target: < 0.5 m/s)")
    print(f"  Distance SS error:  {metrics.get('dist_ss_error', 0):.4f} m (target: < 2 m)")
    print(f"  Min distance:       {metrics.get('min_distance', 0):.2f} m (target: > 5 m)")


if __name__ == '__main__':
    main()

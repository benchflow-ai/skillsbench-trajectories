"""ACC simulation using sensor data and tuned PID parameters."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(path):
    """Load sensor data from CSV file."""
    data = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] != '' else None
            distance = float(row['distance']) if row['distance'] != '' else None
            data.append({
                'time': t,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance,
            })
    return data


def run_simulation():
    """Run 150s ACC simulation and write results to CSV."""
    # Load vehicle params
    with open('vehicle_params.yaml', 'r') as f:
        vehicle_config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Build ACC config: vehicle params + tuned PID gains
    config = {
        'vehicle': vehicle_config['vehicle'],
        'acc_settings': vehicle_config['acc_settings'],
        'pid_speed': tuning['pid_speed'],
        'pid_distance': tuning['pid_distance'],
    }

    dt = vehicle_config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    # Load sensor data for lead vehicle information
    sensor_data = load_sensor_data('sensor_data.csv')

    # Simulation state
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    initial_gap = sensor_data[300]['distance']  # distance at t=30.0 when lead appears

    results = []

    for i, row in enumerate(sensor_data):
        t = row['time']
        lead_speed = row['lead_speed']
        has_lead = lead_speed is not None

        # Track lead vehicle position
        if has_lead and lead_pos is None:
            lead_pos = ego_pos + initial_gap

        if has_lead:
            distance = lead_pos - ego_pos
        else:
            distance = None
            lead_pos = None

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for logging
        ttc = None
        if has_lead and distance is not None:
            closing = ego_speed - lead_speed
            if closing > 0 and distance > 0:
                ttc = distance / closing

        # Log results
        def fmt(val):
            """Round and eliminate negative zero."""
            r = round(val, 2)
            return r if r != 0 else 0.0

        results.append({
            'time': round(t, 1),
            'ego_speed': fmt(ego_speed),
            'acceleration_cmd': fmt(accel_cmd),
            'mode': mode,
            'distance_error': fmt(dist_error) if dist_error is not None else '',
            'distance': fmt(distance) if distance is not None else '',
            'ttc': fmt(ttc) if ttc is not None else '',
        })

        # Update physics
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_pos += ego_speed * dt

        if has_lead:
            lead_pos += lead_speed * dt

    # Write results
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'time', 'ego_speed', 'acceleration_cmd', 'mode',
            'distance_error', 'distance', 'ttc'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} rows to simulation_results.csv")
    return results


def print_metrics(results, config):
    """Print performance metrics."""
    set_speed = config['acc_settings']['set_speed']

    speeds = [r['ego_speed'] for r in results]
    times = [r['time'] for r in results]

    # Rise time (first time >= 90% of set_speed)
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    # Overshoot
    max_speed = max(speeds)
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100.0)

    # Speed steady-state error (cruise phases)
    ss_cruise1 = [abs(set_speed - r['ego_speed']) for r in results
                  if 25.0 <= r['time'] <= 29.9 and r['mode'] == 'cruise']
    ss_cruise2 = [abs(set_speed - r['ego_speed']) for r in results
                  if 140.0 <= r['time'] <= 150.0 and r['mode'] == 'cruise']

    ss1 = sum(ss_cruise1) / len(ss_cruise1) if ss_cruise1 else float('inf')
    ss2 = sum(ss_cruise2) / len(ss_cruise2) if ss_cruise2 else float('inf')
    speed_ss = max(ss1, ss2)

    # Distance steady-state error (follow phase, t=35-65)
    dist_errors = [abs(r['distance_error']) for r in results
                   if 35.0 <= r['time'] <= 65.0 and r['distance_error'] != '']
    dist_ss = sum(dist_errors) / len(dist_errors) if dist_errors else float('inf')

    # Minimum distance
    distances = [r['distance'] for r in results if r['distance'] != '']
    min_dist = min(distances) if distances else float('inf')

    # Mode counts
    modes = {}
    for r in results:
        modes[r['mode']] = modes.get(r['mode'], 0) + 1

    print("\n=== ACC Simulation Performance Metrics ===")
    print(f"Rise time (to 90% of {set_speed} m/s): {rise_time:.1f}s  [target: <10s]")
    print(f"Speed overshoot: {overshoot:.2f}%  [target: <5%]")
    print(f"Speed steady-state error: {speed_ss:.4f} m/s  [target: <0.5 m/s]")
    print(f"Distance steady-state error: {dist_ss:.3f} m  [target: <2m]")
    print(f"Minimum distance: {min_dist:.1f} m  [target: >5m]")
    print(f"Max speed: {max_speed:.2f} m/s")
    print(f"Mode distribution: {modes}")

    # Check all specs
    all_pass = (
        rise_time is not None and rise_time < 10.0 and
        overshoot < 5.0 and
        speed_ss < 0.5 and
        dist_ss < 2.0 and
        min_dist > 5.0
    )
    print(f"\nAll specs met: {'YES' if all_pass else 'NO'}")
    return all_pass


if __name__ == '__main__':
    with open('vehicle_params.yaml', 'r') as f:
        vehicle_config = yaml.safe_load(f)
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    config = {
        'vehicle': vehicle_config['vehicle'],
        'acc_settings': vehicle_config['acc_settings'],
        'pid_speed': tuning['pid_speed'],
        'pid_distance': tuning['pid_distance'],
    }

    results = run_simulation()
    print_metrics(results, config)

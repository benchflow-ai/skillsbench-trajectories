import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath):
    """Load sensor data from CSV file."""
    data = []
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def run_simulation(config, sensor_data, dt):
    """Run ACC simulation using sensor data for lead vehicle information.

    The ego vehicle speed is simulated from 0. Lead vehicle position is
    tracked by integrating lead_speed from sensor data. The distance between
    ego and lead is computed from their respective positions.

    Args:
        config: Vehicle and ACC configuration dict.
        sensor_data: List of dicts with time, lead_speed, distance.
        dt: Simulation timestep.

    Returns:
        List of result dicts for each timestep.
    """
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    results = []

    for i, entry in enumerate(sensor_data):
        lead_speed = entry['lead_speed']

        # Determine distance and lead position
        if lead_speed is not None:
            if lead_pos is None:
                # Lead vehicle just appeared - use sensor distance to initialize
                lead_pos = ego_pos + entry['distance']
            distance = lead_pos - ego_pos
        else:
            if lead_pos is not None:
                lead_pos = None
            distance = None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            closing_speed = ego_speed - lead_speed
            if closing_speed > 0 and distance > 0:
                ttc = distance / closing_speed

        results.append({
            'time': round(entry['time'], 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else '',
        })

        # Update positions and speeds for next timestep
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt

        if lead_pos is not None and lead_speed is not None:
            lead_pos += lead_speed * dt

    return results


def save_results(results, filepath):
    """Save simulation results to CSV."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    # Load vehicle parameters
    with open('vehicle_params.yaml') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('tuning_results.yaml') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    dt = config['simulation']['dt']

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')
    print(f"Simulation complete. {len(results)} rows written to simulation_results.csv")

    # Print performance metrics
    analyze_results(results, config)


def analyze_results(results, config):
    """Analyze and print simulation performance metrics."""
    set_speed = config['acc_settings']['set_speed']

    cruise_before = [r for r in results if r['time'] < 30.0]
    follow_phase = [r for r in results if r['distance'] != '']
    cruise_after = [r for r in results if r['time'] >= 130.0]

    # Rise time: time to reach 90% of set speed from start
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break
    print(f"\n=== Performance Metrics ===")
    print(f"Rise time (to 90% of {set_speed} m/s): {rise_time:.1f}s" if rise_time else "Rise time: NOT REACHED")

    # Overshoot during initial cruise
    max_speed_before_lead = max(r['ego_speed'] for r in cruise_before)
    overshoot_pct = ((max_speed_before_lead - set_speed) / set_speed) * 100
    print(f"Max speed before lead vehicle: {max_speed_before_lead:.2f} m/s")
    print(f"Speed overshoot: {overshoot_pct:.2f}%")

    # Steady-state speed error (last 5s of initial cruise)
    ss_cruise = [r for r in results if 25.0 <= r['time'] < 30.0]
    if ss_cruise:
        ss_error = sum(abs(r['ego_speed'] - set_speed) for r in ss_cruise) / len(ss_cruise)
        print(f"Speed steady-state error (t=25-30s): {ss_error:.3f} m/s")

    # Distance steady-state error during stable following (t=50-120)
    if follow_phase:
        stable_follow = [r for r in follow_phase if 50.0 <= r['time'] < 120.0]
        if stable_follow:
            dist_errors = [abs(float(r['distance_error'])) for r in stable_follow if r['distance_error'] != '']
            if dist_errors:
                ss_dist_error = sum(dist_errors) / len(dist_errors)
                print(f"Distance steady-state error (t=50-120s): {ss_dist_error:.3f} m")

    # Minimum distance during follow
    if follow_phase:
        distances = [float(r['distance']) for r in follow_phase if r['distance'] != '']
        if distances:
            min_dist = min(distances)
            print(f"Minimum distance to lead: {min_dist:.2f} m")

    # Check for emergency events
    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')
    print(f"Emergency braking events: {emergency_count} timesteps")

    # Speed recovery after lead vehicle leaves
    if cruise_after:
        recovery_speed = cruise_after[-1]['ego_speed']
        ss_error_after = abs(recovery_speed - set_speed)
        print(f"Final speed (t=150s): {recovery_speed:.2f} m/s")
        print(f"Final speed error: {ss_error_after:.3f} m/s")


if __name__ == '__main__':
    main()

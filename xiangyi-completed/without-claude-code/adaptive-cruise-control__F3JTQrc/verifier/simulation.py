"""ACC Simulation - Run 150s simulation with tuned PID parameters."""

import yaml
import csv
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and ACC settings."""
    with open('vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_tuned_gains():
    """Load tuned PID gains from tuning_results.yaml."""
    with open('tuning_results.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data():
    """Load sensor data from CSV."""
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })
    return data


def calculate_ttc(ego_speed, lead_speed, distance):
    """Calculate Time-To-Collision."""
    if lead_speed is None or distance is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None

    return distance / relative_speed


def run_simulation():
    """Run ACC simulation for 150 seconds."""
    print("Loading configuration...")
    config = load_config()
    gains = load_tuned_gains()
    sensor_data = load_sensor_data()

    print("Initializing ACC system...")
    acc = AdaptiveCruiseControl(config)

    # Set tuned PID gains
    speed_gains = gains['pid_speed']
    acc.set_speed_pid(speed_gains['kp'], speed_gains['ki'], speed_gains['kd'])

    distance_gains = gains['pid_distance']
    acc.set_distance_pid(distance_gains['kp'], distance_gains['ki'], distance_gains['kd'])

    print(f"Speed PID: kp={speed_gains['kp']}, ki={speed_gains['ki']}, kd={speed_gains['kd']}")
    print(f"Distance PID: kp={distance_gains['kp']}, ki={distance_gains['ki']}, kd={distance_gains['kd']}")

    # Simulation parameters
    dt = config['simulation']['dt']

    # Initial state
    ego_speed = 0.0
    results = []

    print(f"\nRunning simulation for {len(sensor_data)} time steps...")

    for i, sensor in enumerate(sensor_data):
        # Get ACC control command
        accel_cmd, mode, dist_error = acc.compute(
            ego_speed,
            sensor['lead_speed'],
            sensor['distance'],
            dt
        )

        # Calculate TTC for output (before speed update)
        ttc = calculate_ttc(ego_speed, sensor['lead_speed'], sensor['distance'])

        # Store results (using current state before update)
        result = {
            'time': sensor['time'],
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': sensor['distance'],
            'ttc': ttc
        }
        results.append(result)

        # Update ego vehicle speed for next iteration
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Progress indicator
        if (i + 1) % 300 == 0:
            print(f"  Progress: {i+1}/{len(sensor_data)} ({100*(i+1)/len(sensor_data):.1f}%)")

    print(f"Simulation complete! Generated {len(results)} data points.")

    # Save results to CSV
    print("\nSaving results to simulation_results.csv...")
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])

        for r in results:
            writer.writerow([
                f"{r['time']:.1f}",
                f"{r['ego_speed']:.1f}",
                f"{r['acceleration_cmd']:.1f}",
                r['mode'],
                f"{r['distance_error']:.2f}" if r['distance_error'] is not None else '',
                f"{r['distance']:.2f}" if r['distance'] is not None else '',
                f"{r['ttc']:.2f}" if r['ttc'] is not None else ''
            ])

    print("Results saved successfully!")

    # Calculate and print performance metrics
    print("\n" + "="*60)
    print("PERFORMANCE METRICS")
    print("="*60)

    analyze_performance(results, config)


def analyze_performance(results, config):
    """Analyze and print performance metrics."""
    set_speed = config['acc_settings']['set_speed']

    # Cruise phase analysis
    cruise_results = [r for r in results if r['mode'] == 'cruise']

    if cruise_results:
        print("\nCruise Mode Performance:")

        # Rise time
        target_speed_90 = 0.9 * set_speed
        rise_time_results = [r for r in cruise_results if r['ego_speed'] >= target_speed_90]
        if rise_time_results:
            rise_time = rise_time_results[0]['time']
            print(f"  Rise time (to 90% of set speed): {rise_time:.2f}s (target: <10s)")

        # Overshoot
        cruise_speeds = [r['ego_speed'] for r in cruise_results]
        max_speed = max(cruise_speeds)
        overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
        print(f"  Overshoot: {overshoot_pct:.2f}% (target: <5%)")

        # Steady-state error
        steady_start = int(len(cruise_results) * 0.8)
        if steady_start < len(cruise_results):
            steady_speeds = [r['ego_speed'] for r in cruise_results[steady_start:]]
            speed_ss_error = abs(sum(steady_speeds) / len(steady_speeds) - set_speed)
            print(f"  Speed steady-state error: {speed_ss_error:.3f} m/s (target: <0.5 m/s)")

    # Following phase analysis
    follow_results = [r for r in results if r['mode'] == 'follow' and r['distance_error'] is not None]

    if follow_results:
        print("\nFollow Mode Performance:")

        # Distance steady-state error
        steady_start = int(len(follow_results) * 0.8)
        if steady_start < len(follow_results):
            steady_dist_errors = [abs(r['distance_error']) for r in follow_results[steady_start:]]
            dist_ss_error = sum(steady_dist_errors) / len(steady_dist_errors)
            print(f"  Distance steady-state error: {dist_ss_error:.2f}m (target: <2m)")

        # Minimum distance
        distances = [r['distance'] for r in follow_results if r['distance'] is not None]
        if distances:
            min_dist = min(distances)
            print(f"  Minimum distance maintained: {min_dist:.2f}m (target: >5m)")

    # Emergency braking analysis
    emergency_results = [r for r in results if r['mode'] == 'emergency']
    if emergency_results:
        print(f"\nEmergency Mode:")
        print(f"  Emergency braking triggered: {len(emergency_results)} times")
    else:
        print(f"\nEmergency Mode:")
        print(f"  Emergency braking triggered: 0 times")

    # Overall statistics
    print(f"\nOverall Statistics:")
    print(f"  Total simulation time: {results[-1]['time']:.1f}s")
    print(f"  Cruise mode: {len(cruise_results)} steps ({100*len(cruise_results)/len(results):.1f}%)")
    print(f"  Follow mode: {len(follow_results)} steps ({100*len(follow_results)/len(results):.1f}%)")
    print(f"  Emergency mode: {len(emergency_results)} steps ({100*len(emergency_results)/len(results):.1f}%)")


if __name__ == '__main__':
    run_simulation()

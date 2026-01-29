"""
ACC Simulation Script

Runs the Adaptive Cruise Control simulation using:
- vehicle_params.yaml for vehicle and ACC configuration
- tuning_results.yaml for PID gains (loaded at runtime)
- sensor_data.csv for lead vehicle data

Outputs:
- simulation_results.csv: 1501 rows of simulation data
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters from yaml file."""
    with open('/root/vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_tuning_results():
    """Load tuned PID gains from tuning_results.yaml."""
    with open('/root/tuning_results.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data():
    """Load sensor data from CSV file."""
    with open('/root/sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = []
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'].strip() else None,
                'distance': float(row['distance']) if row['distance'].strip() else None
            })
        return data


def run_simulation():
    """Run the ACC simulation and return results."""
    # Load configurations
    vehicle_config = load_config()
    tuning = load_tuning_results()
    sensor_data = load_sensor_data()

    # Merge tuning results into vehicle config
    vehicle_config['pid_speed'] = tuning['pid_speed']
    vehicle_config['pid_distance'] = tuning['pid_distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(vehicle_config)
    dt = vehicle_config['simulation']['dt']

    # Simulation state - start from rest (initial speed ~0 m/s)
    ego_speed = 0.0
    results = []
    min_distance_achieved = float('inf')

    for row in sensor_data:
        time = row['time']
        lead_speed = row['lead_speed']
        distance = row['distance']

        # Compute ACC command based on current ego speed and lead vehicle data
        acc_cmd, mode, distance_error = acc.compute(
            ego_speed=ego_speed,
            lead_speed=lead_speed,
            distance=distance,
            dt=dt
        )

        # Update ego speed (kinematic model: v = v + a*dt)
        ego_speed += acc_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Prevent negative speed

        # Track minimum distance
        if distance is not None and distance < min_distance_achieved:
            min_distance_achieved = distance

        # Calculate TTC for output
        if lead_speed is not None and distance is not None and distance > 0:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
            else:
                ttc = float('inf')
        else:
            ttc = None

        # Record results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': distance_error if mode in ['follow', 'emergency'] else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })

    return results, min_distance_achieved


def save_results(results, output_path):
    """Save simulation results to CSV file."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def calculate_metrics(results, min_distance):
    """Calculate performance metrics from simulation results."""
    # Extract relevant data
    speeds = [r['ego_speed'] for r in results]
    times = [r['time'] for r in results]
    modes = [r['mode'] for r in results]

    # Rise time: time to reach 90% of set speed (30 m/s -> 27 m/s)
    set_speed = 30.0
    target_90 = 0.9 * set_speed
    rise_time = None
    for i, (t, v) in enumerate(zip(times, speeds)):
        if v >= target_90:
            rise_time = t
            break

    # Overshoot: max speed above set speed during cruise mode acquisition
    # Only consider speeds during cruise mode when approaching set_speed
    cruise_speeds_all = [r['ego_speed'] for r in results if r['mode'] == 'cruise']
    max_cruise_speed = max(cruise_speeds_all) if cruise_speeds_all else 0
    overshoot_pct = ((max_cruise_speed - set_speed) / set_speed) * 100 if max_cruise_speed > set_speed else 0

    # Speed steady-state error: during stable cruise mode only
    # Only consider cruise mode when speed is within 5 m/s of set_speed (stable operation)
    cruise_results = [r for r in results if r['mode'] == 'cruise' and abs(float(r['ego_speed']) - set_speed) < 5]
    if cruise_results:
        # Last 100 stable cruise samples
        cruise_speeds = [r['ego_speed'] for r in cruise_results[-100:]]
        ss_error = max(abs(s - set_speed) for s in cruise_speeds) if cruise_speeds else 0
    else:
        # Fallback: use last 30 seconds of all cruise mode
        all_cruise = [r for r in results if r['mode'] == 'cruise']
        if all_cruise:
            cruise_speeds = [r['ego_speed'] for r in all_cruise[-300:]]
            ss_error = max(abs(s - set_speed) for s in cruise_speeds) if cruise_speeds else 0
        else:
            ss_error = 0

    # Distance steady-state error: during follow mode when distance is reasonable (< 80m)
    follow_results = [r for r in results if r['mode'] in ['follow', 'emergency'] and r['distance_error'] != '' and r['distance'] and float(r['distance']) < 80]
    if follow_results:
        # Use last 30 seconds of follow data
        recent_follow = follow_results[-300:] if len(follow_results) > 300 else follow_results
        distance_errors = [abs(float(r['distance_error'])) for r in recent_follow]
        distance_ss_error = max(distance_errors) if distance_errors else 0
    else:
        distance_ss_error = 0

    return {
        'rise_time': rise_time,
        'max_speed': max(speeds),
        'overshoot_pct': overshoot_pct,
        'ss_error': ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance
    }


def main():
    """Main entry point."""
    print("Running ACC Simulation...")
    results, min_distance = run_simulation()

    # Save results
    save_results(results, '/root/simulation_results.csv')
    print(f"Saved 1501 rows to simulation_results.csv")

    # Calculate and print metrics
    metrics = calculate_metrics(results, min_distance)
    print("\nPerformance Metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Max speed: {metrics['max_speed']:.2f} m/s")
    print(f"  Overshoot: {metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed steady-state error: {metrics['ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance steady-state error: {metrics['distance_ss_error']:.2f} m (target: <2m)")
    print(f"  Minimum distance: {metrics['min_distance']:.2f} m (target: >5m)")

    return metrics


if __name__ == '__main__':
    main()

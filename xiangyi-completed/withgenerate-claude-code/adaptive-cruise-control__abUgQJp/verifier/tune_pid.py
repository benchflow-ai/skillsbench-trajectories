"""PID Tuning helper script to find optimal gains."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(filepath: str) -> dict:
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> list:
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def run_simulation(acc: AdaptiveCruiseControl, sensor_data: list, dt: float = 0.1) -> list:
    ego_speed = 0.0
    distance = None
    prev_had_lead = False
    results = []

    for sensor in sensor_data:
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Handle distance tracking
        if lead_speed is not None and sensor_distance is not None:
            if not prev_had_lead:
                distance = sensor_distance
            else:
                distance += (lead_speed - ego_speed) * dt
                distance = max(0.0, distance)
            prev_had_lead = True
        else:
            distance = None
            prev_had_lead = False

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance,
            'ttc': ttc
        })

        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

    return results


def evaluate_performance(results: list, set_speed: float = 30.0):
    """Evaluate simulation performance."""
    # Speed control metrics (cruise mode only - before lead vehicle at t=30)
    early_cruise = [r for r in results if r['mode'] == 'cruise' and r['time'] < 30]

    # Rise time (time to reach 90% of set speed, during initial cruise only)
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in early_cruise:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break

    # Overshoot during initial cruise (before lead vehicle appears)
    if early_cruise:
        max_speed_early = max(r['ego_speed'] for r in early_cruise)
        overshoot_pct = max(0, (max_speed_early - set_speed) / set_speed * 100)
    else:
        overshoot_pct = 0

    # Steady-state error for speed (last 5 seconds of initial cruise, t=25-30)
    steady_cruise = [r for r in early_cruise if 25 <= r['time'] <= 30]
    if steady_cruise:
        avg_speed = sum(r['ego_speed'] for r in steady_cruise) / len(steady_cruise)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = None

    # Also check end cruise phase (t > 145) for final cruise performance
    late_cruise = [r for r in results if r['mode'] == 'cruise' and r['time'] > 145]
    if late_cruise:
        avg_speed_late = sum(r['ego_speed'] for r in late_cruise) / len(late_cruise)
        speed_ss_error_late = abs(set_speed - avg_speed_late)
    else:
        speed_ss_error_late = None

    # Distance control metrics (follow mode)
    follow_results = [r for r in results if r['mode'] == 'follow']
    distances = [r['distance'] for r in follow_results if r['distance'] is not None]

    min_distance = min(distances) if distances else float('inf')

    # Distance steady-state error (follow mode sections)
    if follow_results:
        dist_errors = [abs(r['distance_error']) for r in follow_results
                       if r['distance_error'] is not None]
        avg_dist_error = sum(dist_errors) / len(dist_errors) if dist_errors else None
    else:
        avg_dist_error = None

    # All distances (including emergency)
    all_distances = [r['distance'] for r in results if r['distance'] is not None]
    absolute_min_dist = min(all_distances) if all_distances else float('inf')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'speed_ss_error_late': speed_ss_error_late,
        'min_distance_follow': min_distance,
        'absolute_min_distance': absolute_min_dist,
        'avg_dist_error': avg_dist_error
    }


def test_gains(vehicle_config, sensor_data, speed_kp, speed_ki, speed_kd,
               dist_kp, dist_ki, dist_kd):
    """Test a specific set of gains."""
    acc = AdaptiveCruiseControl(vehicle_config)
    acc.set_speed_controller(speed_kp, speed_ki, speed_kd)
    acc.set_distance_controller(dist_kp, dist_ki, dist_kd)

    results = run_simulation(acc, sensor_data)
    metrics = evaluate_performance(results)

    return metrics, results


def main():
    vehicle_config = load_config('vehicle_params.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')

    print("Testing PID parameters...")
    print("=" * 60)

    # Speed controller tuning
    # With max_accel = 3.0, to reach 30 m/s takes at least 10s
    # Need aggressive Kp to saturate at max_accel initially

    # Distance controller tuning
    # Need to be responsive but not oscillate

    best_speed_gains = None
    best_dist_gains = None
    best_score = float('inf')

    # Grid search for speed controller
    for speed_kp in [0.8, 1.0, 1.2, 1.5]:
        for speed_ki in [0.05, 0.1, 0.15]:
            for speed_kd in [0.2, 0.3, 0.5]:
                # Grid search for distance controller
                for dist_kp in [0.3, 0.5, 0.7]:
                    for dist_ki in [0.02, 0.05, 0.1]:
                        for dist_kd in [0.1, 0.2, 0.3]:
                            metrics, _ = test_gains(
                                vehicle_config, sensor_data,
                                speed_kp, speed_ki, speed_kd,
                                dist_kp, dist_ki, dist_kd
                            )

                            # Check constraints
                            valid = True
                            if metrics['rise_time'] is None or metrics['rise_time'] >= 10:
                                valid = False
                            if metrics['overshoot_pct'] >= 5:
                                valid = False
                            if metrics['speed_ss_error'] is not None and metrics['speed_ss_error'] >= 0.5:
                                valid = False
                            if metrics['absolute_min_distance'] <= 5:
                                valid = False

                            if valid:
                                # Compute score (lower is better)
                                score = (
                                    metrics['rise_time'] +
                                    metrics['overshoot_pct'] +
                                    (metrics['speed_ss_error'] or 0) * 10 +
                                    (metrics['avg_dist_error'] or 0) * 0.5
                                )

                                if score < best_score:
                                    best_score = score
                                    best_speed_gains = (speed_kp, speed_ki, speed_kd)
                                    best_dist_gains = (dist_kp, dist_ki, dist_kd)

    if best_speed_gains is None:
        print("No valid configuration found in grid search.")
        print("Trying manual configuration...")
        # Fallback to reasonable defaults
        best_speed_gains = (1.2, 0.1, 0.3)
        best_dist_gains = (0.5, 0.05, 0.2)

    print(f"\nBest Speed PID: Kp={best_speed_gains[0]}, Ki={best_speed_gains[1]}, Kd={best_speed_gains[2]}")
    print(f"Best Distance PID: Kp={best_dist_gains[0]}, Ki={best_dist_gains[1]}, Kd={best_dist_gains[2]}")

    # Final evaluation
    metrics, results = test_gains(
        vehicle_config, sensor_data,
        *best_speed_gains, *best_dist_gains
    )

    print("\nFinal Performance Metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Min distance: {metrics['absolute_min_distance']:.2f}m (target: >5m)")
    print(f"  Avg distance error: {metrics['avg_dist_error']:.2f}m (target: <2m)")

    # Save tuning results
    tuning_results = {
        'pid_speed': {
            'kp': best_speed_gains[0],
            'ki': best_speed_gains[1],
            'kd': best_speed_gains[2]
        },
        'pid_distance': {
            'kp': best_dist_gains[0],
            'ki': best_dist_gains[1],
            'kd': best_dist_gains[2]
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

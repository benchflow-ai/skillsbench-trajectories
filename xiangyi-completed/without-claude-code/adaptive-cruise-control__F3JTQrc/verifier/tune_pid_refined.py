"""Refined PID tuning script with better distance control."""

import yaml
import csv
import numpy as np
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and ACC settings."""
    with open('vehicle_params.yaml', 'r') as f:
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


def simulate_with_params(config, speed_gains, distance_gains, sensor_data):
    """Run simulation with given PID parameters."""
    acc = AdaptiveCruiseControl(config)
    acc.set_speed_pid(*speed_gains)
    acc.set_distance_pid(*distance_gains)

    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    ego_speed = 0.0
    results = []

    for sensor in sensor_data:
        accel_cmd, mode, dist_error = acc.compute(
            ego_speed,
            sensor['lead_speed'],
            sensor['distance'],
            dt
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        results.append({
            'time': sensor['time'],
            'ego_speed': ego_speed,
            'accel_cmd': accel_cmd,
            'mode': mode,
            'dist_error': dist_error,
            'distance': sensor['distance']
        })

    metrics = evaluate_performance(results, set_speed, config)
    return metrics, results


def evaluate_performance(results, set_speed, config):
    """Evaluate performance metrics."""
    metrics = {}

    cruise_results = [r for r in results if r['mode'] == 'cruise']

    if cruise_results:
        target_speed_90 = 0.9 * set_speed
        rise_time_results = [r for r in cruise_results if r['ego_speed'] >= target_speed_90]
        if rise_time_results:
            metrics['rise_time'] = rise_time_results[0]['time']
        else:
            metrics['rise_time'] = float('inf')

        cruise_speeds = [r['ego_speed'] for r in cruise_results]
        max_speed = max(cruise_speeds)
        metrics['overshoot'] = max(0, (max_speed - set_speed) / set_speed * 100)

        steady_start = int(len(cruise_results) * 0.8)
        if steady_start < len(cruise_results):
            steady_speeds = [r['ego_speed'] for r in cruise_results[steady_start:]]
            metrics['speed_ss_error'] = abs(np.mean(steady_speeds) - set_speed)
        else:
            metrics['speed_ss_error'] = float('inf')
    else:
        metrics['rise_time'] = float('inf')
        metrics['overshoot'] = float('inf')
        metrics['speed_ss_error'] = float('inf')

    follow_results = [r for r in results if r['mode'] == 'follow' and r['dist_error'] is not None]

    if follow_results:
        steady_start = int(len(follow_results) * 0.8)
        if steady_start < len(follow_results):
            steady_dist_errors = [abs(r['dist_error']) for r in follow_results[steady_start:]]
            metrics['distance_ss_error'] = np.mean(steady_dist_errors)
        else:
            metrics['distance_ss_error'] = float('inf')

        distances = [r['distance'] for r in follow_results if r['distance'] is not None]
        if distances:
            metrics['min_distance'] = min(distances)
        else:
            metrics['min_distance'] = float('inf')
    else:
        metrics['distance_ss_error'] = 0.0
        metrics['min_distance'] = float('inf')

    return metrics


def calculate_score(metrics, targets):
    """Calculate overall score. Lower is better."""
    score = 0.0

    # Rise time
    if metrics['rise_time'] > targets['rise_time']:
        score += (metrics['rise_time'] - targets['rise_time']) * 2.0
    else:
        score += (metrics['rise_time'] / targets['rise_time']) * 0.5

    # Overshoot
    if metrics['overshoot'] > targets['overshoot']:
        score += (metrics['overshoot'] - targets['overshoot']) * 3.0
    else:
        score += metrics['overshoot'] * 0.2

    # Speed steady-state error
    if metrics['speed_ss_error'] > targets['speed_ss_error']:
        score += (metrics['speed_ss_error'] - targets['speed_ss_error']) * 4.0
    else:
        score += metrics['speed_ss_error'] * 0.5

    # Distance steady-state error (increased weight)
    if metrics['distance_ss_error'] > targets['distance_ss_error']:
        score += (metrics['distance_ss_error'] - targets['distance_ss_error']) * 5.0
    else:
        score += metrics['distance_ss_error'] * 0.3

    # Minimum distance (critical safety)
    if metrics['min_distance'] < targets['min_distance']:
        score += (targets['min_distance'] - metrics['min_distance']) * 20.0

    return score


def tune_pid():
    """Tune PID parameters with refined search."""
    config = load_config()
    sensor_data = load_sensor_data()

    targets = {
        'rise_time': 10.0,
        'overshoot': 5.0,
        'speed_ss_error': 0.5,
        'distance_ss_error': 2.0,
        'min_distance': 5.0
    }

    # Start with good speed controller from previous tuning
    # Focus on improving distance controller
    speed_kp_range = [2.0, 2.5, 3.0, 3.5]
    speed_ki_range = [0.0, 0.01, 0.05]
    speed_kd_range = [0.0, 0.05, 0.1]

    # Wider range for distance controller
    distance_kp_range = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    distance_ki_range = [0.0, 0.01, 0.05, 0.1]
    distance_kd_range = [0.0, 0.5, 1.0, 1.5, 2.0]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    print("Starting refined PID tuning...")
    total = (len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) *
             len(distance_kp_range) * len(distance_ki_range) * len(distance_kd_range))
    print(f"Testing {total} combinations")

    iteration = 0
    for s_kp in speed_kp_range:
        for s_ki in speed_ki_range:
            for s_kd in speed_kd_range:
                for d_kp in distance_kp_range:
                    for d_ki in distance_ki_range:
                        for d_kd in distance_kd_range:
                            iteration += 1

                            speed_gains = (s_kp, s_ki, s_kd)
                            distance_gains = (d_kp, d_ki, d_kd)

                            try:
                                metrics, _ = simulate_with_params(
                                    config, speed_gains, distance_gains, sensor_data
                                )

                                score = calculate_score(metrics, targets)

                                if score < best_score:
                                    best_score = score
                                    best_params = {
                                        'speed': speed_gains,
                                        'distance': distance_gains
                                    }
                                    best_metrics = metrics

                                    print(f"\nIter {iteration}/{total}: New best score = {score:.3f}")
                                    print(f"  Speed: kp={s_kp}, ki={s_ki}, kd={s_kd}")
                                    print(f"  Distance: kp={d_kp}, ki={d_ki}, kd={d_kd}")
                                    print(f"  Rise time: {metrics['rise_time']:.2f}s, "
                                          f"Overshoot: {metrics['overshoot']:.2f}%, "
                                          f"Speed SS: {metrics['speed_ss_error']:.3f} m/s")
                                    print(f"  Dist SS: {metrics['distance_ss_error']:.3f}m, "
                                          f"Min dist: {metrics['min_distance']:.2f}m")

                            except Exception as e:
                                pass

            if iteration % 100 == 0:
                print(f"Progress: {iteration}/{total} ({100*iteration/total:.1f}%)")

    print("\n" + "="*60)
    print("REFINED TUNING COMPLETE")
    print("="*60)
    print(f"Best score: {best_score:.3f}")
    print(f"\nOptimal Speed PID: kp={best_params['speed'][0]}, ki={best_params['speed'][1]}, kd={best_params['speed'][2]}")
    print(f"Optimal Distance PID: kp={best_params['distance'][0]}, ki={best_params['distance'][1]}, kd={best_params['distance'][2]}")
    print(f"\nPerformance metrics:")
    for key, value in best_metrics.items():
        print(f"  {key}: {value:.3f}")

    # Save results
    results = {
        'pid_speed': {
            'kp': float(best_params['speed'][0]),
            'ki': float(best_params['speed'][1]),
            'kd': float(best_params['speed'][2])
        },
        'pid_distance': {
            'kp': float(best_params['distance'][0]),
            'ki': float(best_params['distance'][1]),
            'kd': float(best_params['distance'][2])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)

    print("\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    tune_pid()

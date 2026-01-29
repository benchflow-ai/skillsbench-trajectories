"""PID tuning script for ACC system."""

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
    """
    Run simulation with given PID parameters.

    Returns:
        dict: Performance metrics
    """
    # Create ACC system
    acc = AdaptiveCruiseControl(config)
    acc.set_speed_pid(*speed_gains)
    acc.set_distance_pid(*distance_gains)

    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    # Simulation state
    ego_speed = 0.0
    results = []

    for i, sensor in enumerate(sensor_data):
        # Get control command
        accel_cmd, mode, dist_error = acc.compute(
            ego_speed,
            sensor['lead_speed'],
            sensor['distance'],
            dt
        )

        # Update ego speed
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Store results
        results.append({
            'time': sensor['time'],
            'ego_speed': ego_speed,
            'accel_cmd': accel_cmd,
            'mode': mode,
            'dist_error': dist_error,
            'distance': sensor['distance']
        })

    # Calculate performance metrics
    metrics = evaluate_performance(results, set_speed, config)
    return metrics, results


def evaluate_performance(results, set_speed, config):
    """Evaluate performance metrics."""
    metrics = {}

    # Find cruise phase (mode == 'cruise' and before lead vehicle appears)
    cruise_results = [r for r in results if r['mode'] == 'cruise']

    if cruise_results:
        # Speed rise time: time to reach 90% of set speed
        target_speed_90 = 0.9 * set_speed
        rise_time_results = [r for r in cruise_results if r['ego_speed'] >= target_speed_90]
        if rise_time_results:
            metrics['rise_time'] = rise_time_results[0]['time']
        else:
            metrics['rise_time'] = float('inf')

        # Speed overshoot
        cruise_speeds = [r['ego_speed'] for r in cruise_results]
        max_speed = max(cruise_speeds)
        metrics['overshoot'] = max(0, (max_speed - set_speed) / set_speed * 100)

        # Speed steady-state error (last 20% of cruise phase)
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

    # Following phase metrics
    follow_results = [r for r in results if r['mode'] == 'follow' and r['dist_error'] is not None]

    if follow_results:
        # Distance steady-state error (last 20% of following phase)
        steady_start = int(len(follow_results) * 0.8)
        if steady_start < len(follow_results):
            steady_dist_errors = [abs(r['dist_error']) for r in follow_results[steady_start:]]
            metrics['distance_ss_error'] = np.mean(steady_dist_errors)
        else:
            metrics['distance_ss_error'] = float('inf')

        # Minimum distance maintained
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
    """
    Calculate overall score based on target achievement.

    Lower score is better. Penalize violations heavily.
    """
    score = 0.0

    # Rise time target: < 10s (weight: 1.0)
    if metrics['rise_time'] > targets['rise_time']:
        score += (metrics['rise_time'] - targets['rise_time']) * 2.0
    else:
        score += (metrics['rise_time'] / targets['rise_time']) * 0.5

    # Overshoot target: < 5% (weight: 2.0)
    if metrics['overshoot'] > targets['overshoot']:
        score += (metrics['overshoot'] - targets['overshoot']) * 3.0
    else:
        score += metrics['overshoot'] * 0.2

    # Speed steady-state error: < 0.5 m/s (weight: 1.5)
    if metrics['speed_ss_error'] > targets['speed_ss_error']:
        score += (metrics['speed_ss_error'] - targets['speed_ss_error']) * 4.0
    else:
        score += metrics['speed_ss_error'] * 0.5

    # Distance steady-state error: < 2m (weight: 1.5)
    if metrics['distance_ss_error'] > targets['distance_ss_error']:
        score += (metrics['distance_ss_error'] - targets['distance_ss_error']) * 3.0
    else:
        score += metrics['distance_ss_error'] * 0.3

    # Minimum distance: > 5m (critical safety constraint, heavy penalty)
    if metrics['min_distance'] < targets['min_distance']:
        score += (targets['min_distance'] - metrics['min_distance']) * 10.0

    return score


def tune_pid():
    """Tune PID parameters using grid search."""
    config = load_config()
    sensor_data = load_sensor_data()

    # Performance targets
    targets = {
        'rise_time': 10.0,
        'overshoot': 5.0,
        'speed_ss_error': 0.5,
        'distance_ss_error': 2.0,
        'min_distance': 5.0
    }

    # Grid search ranges (coarse-grained first)
    speed_kp_range = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    speed_ki_range = [0.0, 0.05, 0.1, 0.2, 0.3]
    speed_kd_range = [0.0, 0.1, 0.3, 0.5, 1.0]

    distance_kp_range = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5]
    distance_ki_range = [0.0, 0.01, 0.05, 0.1]
    distance_kd_range = [0.0, 0.5, 1.0, 1.5, 2.0]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    print("Starting PID tuning...")
    print(f"Testing {len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) * len(distance_kp_range) * len(distance_ki_range) * len(distance_kd_range)} combinations")

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
                                    config,
                                    speed_gains,
                                    distance_gains,
                                    sensor_data
                                )

                                score = calculate_score(metrics, targets)

                                if score < best_score:
                                    best_score = score
                                    best_params = {
                                        'speed': speed_gains,
                                        'distance': distance_gains
                                    }
                                    best_metrics = metrics

                                    print(f"\nIteration {iteration}: New best score = {score:.3f}")
                                    print(f"  Speed PID: kp={s_kp}, ki={s_ki}, kd={s_kd}")
                                    print(f"  Distance PID: kp={d_kp}, ki={d_ki}, kd={d_kd}")
                                    print(f"  Metrics: {metrics}")

                            except Exception as e:
                                # Skip invalid parameter combinations
                                pass

    print("\n" + "="*60)
    print("TUNING COMPLETE")
    print("="*60)
    print(f"Best score: {best_score:.3f}")
    print(f"\nOptimal Speed PID gains:")
    print(f"  kp: {best_params['speed'][0]}")
    print(f"  ki: {best_params['speed'][1]}")
    print(f"  kd: {best_params['speed'][2]}")
    print(f"\nOptimal Distance PID gains:")
    print(f"  kp: {best_params['distance'][0]}")
    print(f"  ki: {best_params['distance'][1]}")
    print(f"  kd: {best_params['distance'][2]}")
    print(f"\nPerformance metrics:")
    for key, value in best_metrics.items():
        print(f"  {key}: {value:.3f}")

    # Save results to YAML
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

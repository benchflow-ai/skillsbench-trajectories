"""
Improved PID parameter tuning script for ACC system.

Uses a more refined search strategy and better evaluation metrics.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl
import itertools


def load_config(config_file):
    """Load base configuration from YAML file."""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = pd.read_csv(sensor_file)
    return data


def run_simulation_eval(config, sensor_data):
    """
    Run simulation and collect detailed metrics.

    Returns:
        dict: Evaluation metrics
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    ego_speed = sensor_data.loc[0, 'ego_speed']
    cruise_speeds = []
    follow_dist_errors = []
    min_distance = float('inf')
    emergency_count = 0

    for step in range(min(1500, len(sensor_data))):
        row = sensor_data.iloc[step]
        lead_speed = row['lead_speed']
        distance = row['distance']

        if pd.isna(lead_speed) or pd.isna(distance):
            lead_speed = None
            distance = None
        else:
            min_distance = min(min_distance, distance)

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        if mode == 'cruise':
            cruise_speeds.append(ego_speed)
        elif mode == 'follow' and dist_error is not None:
            follow_dist_errors.append(dist_error)
        elif mode == 'emergency':
            emergency_count += 1

    # Calculate metrics
    metrics = {}

    if len(cruise_speeds) > 0:
        cruise_speeds = np.array(cruise_speeds)

        # Rise time to 90%
        target_90 = 0.9 * set_speed
        idx_90 = np.where(cruise_speeds >= target_90)[0]
        if len(idx_90) > 0:
            metrics['rise_time'] = idx_90[0] * dt
        else:
            metrics['rise_time'] = float('inf')

        # Overshoot
        max_speed = np.max(cruise_speeds)
        metrics['overshoot'] = max(0, max_speed - set_speed)

        # Steady-state error (last 5 seconds)
        ss_start = max(0, len(cruise_speeds) - 50)
        ss_speeds = cruise_speeds[ss_start:]
        metrics['ss_error'] = abs(np.mean(ss_speeds) - set_speed)
    else:
        metrics['rise_time'] = float('inf')
        metrics['overshoot'] = float('inf')
        metrics['ss_error'] = float('inf')

    if len(follow_dist_errors) > 0:
        dist_errs = np.array(follow_dist_errors)
        metrics['dist_error_mean'] = np.mean(np.abs(dist_errs))
        metrics['dist_error_max'] = np.max(np.abs(dist_errs))
    else:
        metrics['dist_error_mean'] = float('inf')
        metrics['dist_error_max'] = float('inf')

    metrics['min_distance'] = min_distance if min_distance != float('inf') else 0
    metrics['emergency_count'] = emergency_count

    return metrics


def score_metrics(metrics):
    """
    Calculate overall score from metrics.

    Weights are based on target specifications.
    """
    score = 100.0

    # Rise time target < 10s (weight: 15)
    if metrics['rise_time'] < 10:
        score += 15
    else:
        score -= 15 * (min(metrics['rise_time'] - 10, 20) / 20)

    # Overshoot target < 5% of 30m/s = 1.5 m/s (weight: 15)
    if metrics['overshoot'] < 1.5:
        score += 15
    else:
        score -= 15 * (min(metrics['overshoot'] - 1.5, 10) / 10)

    # Steady-state error target < 0.5 m/s (weight: 15)
    if metrics['ss_error'] < 0.5:
        score += 15
    else:
        score -= 15 * (min(metrics['ss_error'] - 0.5, 5) / 5)

    # Distance error target < 2m (weight: 20)
    if metrics['dist_error_mean'] < 2.0:
        score += 20
    else:
        score -= 20 * (min(metrics['dist_error_mean'] - 2.0, 20) / 20)

    # Minimum distance target > 5m (weight: 20)
    if metrics['min_distance'] > 5.0:
        score += 20
    else:
        score -= 20 * max(0, (5.0 - metrics['min_distance']) / 5.0)

    # Emergency activations penalty (weight: 15)
    if metrics['emergency_count'] == 0:
        score += 15
    else:
        score -= 15 * min(metrics['emergency_count'] / 5, 1.0)

    return score


def tune_parameters(config_file, sensor_file, output_file):
    """Tune PID parameters with refined search."""
    print("Loading configuration and sensor data...")
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    # Refined parameter ranges
    speed_kp = [0.1, 0.2, 0.3, 0.5, 0.8]
    speed_ki = [0.0, 0.01, 0.02, 0.03, 0.05, 0.1]
    speed_kd = [0.0, 0.1, 0.2, 0.3, 0.5]

    dist_kp = [0.1, 0.2, 0.3, 0.5, 0.8]
    dist_ki = [0.0, 0.01, 0.02, 0.03, 0.05, 0.1]
    dist_kd = [0.0, 0.1, 0.2, 0.3, 0.5]

    # Two-stage tuning: first optimize speed, then distance
    print("\nStage 1: Tuning speed controller...")
    best_speed_score = float('-inf')
    best_speed_params = None

    total = len(speed_kp) * len(speed_ki) * len(speed_kd)
    count = 0

    for kp, ki, kd in itertools.product(speed_kp, speed_ki, speed_kd):
        count += 1
        config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
        config['pid_distance'] = {'kp': 0.1, 'ki': 0.0, 'kd': 0.0}  # Neutral

        metrics = run_simulation_eval(config, sensor_data)
        score = score_metrics(metrics)

        if score > best_speed_score:
            best_speed_score = score
            best_speed_params = (kp, ki, kd)
            print(f"  New best speed params: Kp={kp}, Ki={ki}, Kd={kd} (score={score:.2f})")

        if count % 30 == 0:
            print(f"  Progress: {count}/{total}")

    print(f"\n  Best speed controller: Kp={best_speed_params[0]}, "
          f"Ki={best_speed_params[1]}, Kd={best_speed_params[2]}")

    # Stage 2: Tune distance controller with best speed controller
    print("\nStage 2: Tuning distance controller...")
    config['pid_speed'] = {
        'kp': best_speed_params[0],
        'ki': best_speed_params[1],
        'kd': best_speed_params[2]
    }

    best_dist_score = float('-inf')
    best_dist_params = None

    total = len(dist_kp) * len(dist_ki) * len(dist_kd)
    count = 0

    for kp, ki, kd in itertools.product(dist_kp, dist_ki, dist_kd):
        count += 1
        config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}

        metrics = run_simulation_eval(config, sensor_data)
        score = score_metrics(metrics)

        if score > best_dist_score:
            best_dist_score = score
            best_dist_params = (kp, ki, kd)
            print(f"  New best distance params: Kp={kp}, Ki={ki}, Kd={kd} (score={score:.2f})")

        if count % 30 == 0:
            print(f"  Progress: {count}/{total}")

    print(f"\n  Best distance controller: Kp={best_dist_params[0]}, "
          f"Ki={best_dist_params[1]}, Kd={best_dist_params[2]}")

    # Final results
    final_config = {
        'pid_speed': {
            'kp': best_speed_params[0],
            'ki': best_speed_params[1],
            'kd': best_speed_params[2]
        },
        'pid_distance': {
            'kp': best_dist_params[0],
            'ki': best_dist_params[1],
            'kd': best_dist_params[2]
        }
    }

    # Save results
    with open(output_file, 'w') as f:
        yaml.dump(final_config, f, default_flow_style=False)

    print(f"\nTuning results saved to {output_file}")

    # Verify
    print("\nFinal verification...")
    config['pid_speed'] = final_config['pid_speed']
    config['pid_distance'] = final_config['pid_distance']
    metrics = run_simulation_eval(config, sensor_data)

    print("\nPerformance Metrics:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {metrics['overshoot']:.3f} m/s (target: <1.5 m/s)")
    print(f"  Speed SS error: {metrics['ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance error: {metrics['dist_error_mean']:.2f}m (target: <2m)")
    print(f"  Min distance: {metrics['min_distance']:.2f}m (target: >5m)")
    print(f"  Emergency activations: {metrics['emergency_count']}")
    print(f"  Overall score: {score_metrics(metrics):.2f}/100")


if __name__ == '__main__':
    tune_parameters(
        '/root/vehicle_params.yaml',
        '/root/sensor_data.csv',
        '/root/tuning_results.yaml'
    )

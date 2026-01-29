"""
Final PID parameter tuning with focus on distance control.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl
import itertools


def load_config(config_file):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_sensor_data(sensor_file):
    data = pd.read_csv(sensor_file)
    return data


def run_simulation_eval(config, sensor_data):
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

    metrics = {}

    if len(cruise_speeds) > 0:
        cruise_speeds = np.array(cruise_speeds)
        target_90 = 0.9 * set_speed
        idx_90 = np.where(cruise_speeds >= target_90)[0]
        metrics['rise_time'] = idx_90[0] * dt if len(idx_90) > 0 else float('inf')
        metrics['overshoot'] = max(0, np.max(cruise_speeds) - set_speed)
        ss_start = max(0, len(cruise_speeds) - 50)
        metrics['ss_error'] = abs(np.mean(cruise_speeds[ss_start:]) - set_speed)
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
    score = 100.0

    # Rise time (weight: 10)
    if metrics['rise_time'] < 10:
        score += 10
    else:
        score -= 10 * min((metrics['rise_time'] - 10) / 5, 1.0)

    # Overshoot (weight: 10)
    if metrics['overshoot'] < 1.5:
        score += 10
    else:
        score -= 10 * min((metrics['overshoot'] - 1.5) / 10, 1.0)

    # Speed SS error (weight: 10)
    if metrics['ss_error'] < 0.5:
        score += 10
    else:
        score -= 10 * min((metrics['ss_error'] - 0.5) / 5, 1.0)

    # Distance error (weight: 30) - CRITICAL
    if metrics['dist_error_mean'] < 2.0:
        score += 30
    else:
        score -= 30 * min((metrics['dist_error_mean'] - 2.0) / 20, 1.0)

    # Minimum distance (weight: 30) - CRITICAL
    if metrics['min_distance'] > 5.0:
        score += 30
    else:
        score -= 30 * max(0, (5.0 - metrics['min_distance']) / 10.0)

    # Emergency count (weight: 10)
    if metrics['emergency_count'] == 0:
        score += 10
    else:
        score -= 10 * min(metrics['emergency_count'] / 50, 1.0)

    return score


def main():
    print("Loading data...")
    config = load_config('/root/vehicle_params.yaml')
    sensor_data = load_sensor_data('/root/sensor_data.csv')

    # Fix speed controller to proven good value
    config['pid_speed'] = {'kp': 0.5, 'ki': 0.0, 'kd': 0.0}

    # Focused distance controller tuning
    print("Tuning distance controller (critical for safety)...\n")

    # Parameters focused on smooth distance control
    dist_kp = [0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
    dist_ki = [0.0, 0.01, 0.02, 0.05, 0.1]
    dist_kd = [0.1, 0.2, 0.3, 0.5, 0.8]

    best_score = float('-inf')
    best_params = None

    total = len(dist_kp) * len(dist_ki) * len(dist_kd)
    count = 0

    for kp, ki, kd in itertools.product(dist_kp, dist_ki, dist_kd):
        count += 1
        config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}

        metrics = run_simulation_eval(config, sensor_data)
        score = score_metrics(metrics)

        if score > best_score:
            best_score = score
            best_params = (kp, ki, kd)
            print(f"  New best: Kp={kp:.2f}, Ki={ki:.2f}, Kd={kd:.2f}")
            print(f"    Distance error: {metrics['dist_error_mean']:.2f}m, "
                  f"Min dist: {metrics['min_distance']:.2f}m, "
                  f"Score: {score:.2f}")

        if count % 50 == 0:
            print(f"  Progress: {count}/{total}")

    # Final configuration
    final_config = {
        'pid_speed': {
            'kp': 0.5,
            'ki': 0.0,
            'kd': 0.0
        },
        'pid_distance': {
            'kp': best_params[0],
            'ki': best_params[1],
            'kd': best_params[2]
        }
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(final_config, f, default_flow_style=False)

    print(f"\nTuning complete!")
    print(f"\nFinal Configuration:")
    print(f"Speed:    Kp={final_config['pid_speed']['kp']}, "
          f"Ki={final_config['pid_speed']['ki']}, "
          f"Kd={final_config['pid_speed']['kd']}")
    print(f"Distance: Kp={final_config['pid_distance']['kp']:.2f}, "
          f"Ki={final_config['pid_distance']['ki']:.2f}, "
          f"Kd={final_config['pid_distance']['kd']:.2f}")

    # Verify
    print("\nVerification...")
    config['pid_distance'] = final_config['pid_distance']
    metrics = run_simulation_eval(config, sensor_data)

    print(f"\nPerformance:")
    print(f"  Rise time: {metrics['rise_time']:.2f}s")
    print(f"  Overshoot: {metrics['overshoot']:.3f} m/s")
    print(f"  Speed SS error: {metrics['ss_error']:.3f} m/s")
    print(f"  Distance error: {metrics['dist_error_mean']:.2f}m")
    print(f"  Min distance: {metrics['min_distance']:.2f}m")
    print(f"  Emergency count: {metrics['emergency_count']}")
    print(f"  Overall score: {score_metrics(metrics):.2f}/100")


if __name__ == '__main__':
    main()

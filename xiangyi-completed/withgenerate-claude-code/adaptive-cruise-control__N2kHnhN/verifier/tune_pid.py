"""
PID parameter tuning script for ACC system.

Evaluates different PID gain combinations and selects best parameters
based on performance against target specifications.
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


def run_simulation_quick(config, sensor_data, max_steps=1500):
    """
    Run quick simulation for tuning evaluation.

    Args:
        config (dict): Configuration with PID gains
        sensor_data (pd.DataFrame): Sensor data
        max_steps (int): Maximum simulation steps

    Returns:
        tuple: (cruise_speeds, follow_distances, follow_dist_errors, emergency_count)
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    ego_speed = sensor_data.loc[0, 'ego_speed']
    cruise_speeds = []
    follow_distances = []
    follow_dist_errors = []
    emergency_count = 0

    for step in range(min(max_steps, len(sensor_data))):
        row = sensor_data.iloc[step]
        lead_speed = row['lead_speed']
        distance = row['distance']

        if pd.isna(lead_speed) or pd.isna(distance):
            lead_speed = None
            distance = None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        if mode == 'cruise':
            cruise_speeds.append(ego_speed)
        elif mode == 'follow':
            follow_distances.append(distance)
            if dist_error is not None:
                follow_dist_errors.append(dist_error)
        elif mode == 'emergency':
            emergency_count += 1

    return cruise_speeds, follow_distances, follow_dist_errors, emergency_count


def evaluate_tuning(config, sensor_data):
    """
    Evaluate tuning parameters against performance targets.

    Returns:
        dict: Score metrics
    """
    set_speed = config['acc_settings']['set_speed']
    cruise_speeds, follow_dists, follow_dist_errs, emergency_count = run_simulation_quick(
        config, sensor_data
    )

    score = 0.0
    penalties = 0.0

    # Evaluate cruise phase
    if len(cruise_speeds) > 0:
        cruise_speeds = np.array(cruise_speeds)

        # Rise time (target < 10s = 100 steps)
        target_90 = 0.9 * set_speed
        idx_90 = np.where(cruise_speeds >= target_90)[0]
        if len(idx_90) > 0:
            rise_time_steps = idx_90[0]
            if rise_time_steps < 100:  # < 10s
                score += 10
            else:
                penalties += (rise_time_steps - 100) * 0.01

        # Overshoot (target < 5%)
        max_speed = np.max(cruise_speeds)
        overshoot_pct = ((max_speed - set_speed) / set_speed) * 100
        if overshoot_pct < 5:
            score += 10
        else:
            penalties += (overshoot_pct - 5) * 0.5

        # Steady-state error (target < 0.5 m/s)
        ss_start = max(0, len(cruise_speeds) - 100)
        ss_speeds = cruise_speeds[ss_start:]
        ss_error = abs(np.mean(ss_speeds) - set_speed)
        if ss_error < 0.5:
            score += 10
        else:
            penalties += (ss_error - 0.5) * 2

    # Evaluate follow phase
    if len(follow_dist_errs) > 0:
        dist_errs = np.array(follow_dist_errs)
        mean_dist_error = np.mean(np.abs(dist_errs))

        # Distance steady-state error (target < 2m)
        if mean_dist_error < 2.0:
            score += 10
        else:
            penalties += (mean_dist_error - 2.0) * 1.0

    # Safety: penalize emergency activations heavily
    penalties += emergency_count * 5.0

    # Penalize minimum distance violations
    if len(follow_dists) > 0:
        follow_dists = np.array(follow_dists)
        min_dist = np.nanmin(follow_dists)
        if min_dist < 5.0:
            penalties += (5.0 - min_dist) * 10.0

    total_score = score - penalties
    return {
        'score': total_score,
        'rise_time': idx_90[0] if len(idx_90) > 0 else None,
        'overshoot_pct': overshoot_pct if len(cruise_speeds) > 0 else None,
        'ss_error': ss_error if len(cruise_speeds) > 0 else None,
        'mean_dist_error': mean_dist_error if len(follow_dist_errs) > 0 else None,
        'emergency_count': emergency_count
    }


def tune_parameters(config_file, sensor_file, output_file):
    """
    Search for optimal PID parameters.

    Searches over grid of parameters and selects best combination.
    """
    print("Loading configuration and sensor data...")
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    # Parameter search space
    kp_values = [0.1, 0.3, 0.5, 0.8, 1.0]
    ki_values = [0.0, 0.01, 0.02, 0.05]
    kd_values = [0.0, 0.1, 0.2, 0.3]

    best_score = float('-inf')
    best_params = None
    results_list = []

    total_combinations = len(kp_values) * len(ki_values) * len(kd_values) * 2
    current = 0

    print(f"\nTuning PID parameters (testing {total_combinations} combinations)...\n")

    # Tune speed controller
    print("Tuning speed controller...")
    for kp, ki, kd in itertools.product(kp_values, ki_values, kd_values):
        current += 1
        config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}

        metrics = evaluate_tuning(config, sensor_data)

        results_list.append({
            'controller': 'speed',
            'kp': kp,
            'ki': ki,
            'kd': kd,
            **metrics
        })

        if metrics['score'] > best_score:
            best_score = metrics['score']
            best_params = {
                'type': 'speed',
                'kp': kp,
                'ki': ki,
                'kd': kd
            }

        if current % 20 == 0:
            print(f"  Progress: {current}/{total_combinations} "
                  f"(Best score: {best_score:.2f})")

    # Use best speed controller for distance tuning
    config['pid_speed'] = {
        'kp': best_params['kp'],
        'ki': best_params['ki'],
        'kd': best_params['kd']
    }
    best_speed_params = best_params.copy()
    best_score = float('-inf')

    print("\nTuning distance controller...")
    for kp, ki, kd in itertools.product(kp_values, ki_values, kd_values):
        current += 1
        config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}

        metrics = evaluate_tuning(config, sensor_data)

        results_list.append({
            'controller': 'distance',
            'kp': kp,
            'ki': ki,
            'kd': kd,
            **metrics
        })

        if metrics['score'] > best_score:
            best_score = metrics['score']
            best_params = {
                'type': 'distance',
                'kp': kp,
                'ki': ki,
                'kd': kd
            }

        if current % 20 == 0:
            print(f"  Progress: {current}/{total_combinations} "
                  f"(Best score: {best_score:.2f})")

    # Prepare final configuration
    final_config = {
        'pid_speed': {
            'kp': best_speed_params['kp'],
            'ki': best_speed_params['ki'],
            'kd': best_speed_params['kd']
        },
        'pid_distance': {
            'kp': best_params['kp'],
            'ki': best_params['ki'],
            'kd': best_params['kd']
        }
    }

    print(f"\nTuning complete!")
    print(f"\nOptimal parameters found:")
    print(f"Speed Controller:    Kp={final_config['pid_speed']['kp']:.4f}, "
          f"Ki={final_config['pid_speed']['ki']:.4f}, "
          f"Kd={final_config['pid_speed']['kd']:.4f}")
    print(f"Distance Controller: Kp={final_config['pid_distance']['kp']:.4f}, "
          f"Ki={final_config['pid_distance']['ki']:.4f}, "
          f"Kd={final_config['pid_distance']['kd']:.4f}")

    # Save to file
    with open(output_file, 'w') as f:
        yaml.dump(final_config, f, default_flow_style=False)

    print(f"\nResults saved to {output_file}")

    # Verify the tuned parameters
    print("\nVerifying tuned parameters...")
    config['pid_speed'] = final_config['pid_speed']
    config['pid_distance'] = final_config['pid_distance']
    metrics = evaluate_tuning(config, sensor_data)

    print("Final Metrics:")
    print(f"  Rise time: {metrics['rise_time']} steps (~{metrics['rise_time']*0.1:.1f}s)")
    print(f"  Overshoot: {metrics['overshoot_pct']:.2f}%")
    print(f"  Speed SS error: {metrics['ss_error']:.3f} m/s")
    print(f"  Distance error: {metrics['mean_dist_error']:.2f}m")
    print(f"  Emergency activations: {metrics['emergency_count']}")


if __name__ == '__main__':
    tune_parameters(
        '/root/vehicle_params.yaml',
        '/root/sensor_data.csv',
        '/root/tuning_results.yaml'
    )

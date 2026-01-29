"""
PID Parameter Tuning Script

This script tunes PID parameters for speed and distance control to meet
performance requirements.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_test_simulation(config):
    """
    Run a test simulation with given PID parameters.

    Args:
        config (dict): Configuration with PID parameters

    Returns:
        tuple: (results_df, metrics)
    """
    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Extract simulation parameters
    dt = config['simulation']['dt']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize simulation state
    ego_speed = 0.0
    results = []

    # Simulation loop
    for idx, row in sensor_data.iterrows():
        time = row['time']

        # Get lead vehicle data
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute control command
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Record results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance
        })

        # Update ego vehicle speed
        ego_speed = ego_speed + acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)

    results_df = pd.DataFrame(results)

    # Calculate metrics
    metrics = calculate_metrics(results_df, config)

    return results_df, metrics


def calculate_metrics(results_df, config):
    """
    Calculate performance metrics.

    Args:
        results_df (pd.DataFrame): Simulation results
        config (dict): Configuration

    Returns:
        dict: Performance metrics
    """
    set_speed = config['acc_settings']['set_speed']
    metrics = {}

    # Speed control metrics (cruise mode)
    cruise_data = results_df[results_df['mode'] == 'cruise']

    if len(cruise_data) > 0:
        # Rise time
        target_speed = 0.9 * set_speed
        rise_idx = cruise_data[cruise_data['ego_speed'] >= target_speed].index
        if len(rise_idx) > 0:
            metrics['rise_time'] = cruise_data.loc[rise_idx[0], 'time']
        else:
            metrics['rise_time'] = 999.0

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = ((max_speed - set_speed) / set_speed) * 100

        # Steady-state error
        final_cruise = cruise_data.iloc[int(0.9 * len(cruise_data)):]
        if len(final_cruise) > 0:
            metrics['speed_ss_error'] = abs(final_cruise['ego_speed'].mean() - set_speed)
        else:
            metrics['speed_ss_error'] = 999.0
    else:
        metrics['rise_time'] = 999.0
        metrics['overshoot_pct'] = 0.0
        metrics['speed_ss_error'] = 999.0

    # Distance control metrics
    follow_data = results_df[results_df['mode'] == 'follow']

    if len(follow_data) > 0:
        metrics['min_distance'] = follow_data['distance'].min()

        valid_errors = follow_data['distance_error'].dropna()
        if len(valid_errors) > 0:
            final_errors = valid_errors.iloc[int(0.8 * len(valid_errors)):]
            if len(final_errors) > 0:
                metrics['distance_ss_error'] = abs(final_errors.mean())
            else:
                metrics['distance_ss_error'] = 999.0
        else:
            metrics['distance_ss_error'] = 999.0
    else:
        metrics['min_distance'] = 999.0
        metrics['distance_ss_error'] = 999.0

    return metrics


def evaluate_performance(metrics):
    """
    Check if performance meets requirements.

    Args:
        metrics (dict): Performance metrics

    Returns:
        tuple: (meets_requirements, score)
    """
    requirements = {
        'rise_time': 10.0,
        'overshoot_pct': 5.0,
        'speed_ss_error': 0.5,
        'distance_ss_error': 2.0,
        'min_distance': 5.0
    }

    meets_requirements = True
    score = 0.0

    # Check each requirement
    if metrics['rise_time'] > requirements['rise_time']:
        meets_requirements = False
    else:
        score += (1.0 - metrics['rise_time'] / requirements['rise_time'])

    if metrics['overshoot_pct'] > requirements['overshoot_pct']:
        meets_requirements = False
    else:
        score += (1.0 - metrics['overshoot_pct'] / requirements['overshoot_pct'])

    if metrics['speed_ss_error'] > requirements['speed_ss_error']:
        meets_requirements = False
    else:
        score += (1.0 - metrics['speed_ss_error'] / requirements['speed_ss_error'])

    if metrics['distance_ss_error'] > requirements['distance_ss_error']:
        meets_requirements = False
    else:
        score += (1.0 - metrics['distance_ss_error'] / requirements['distance_ss_error'])

    if metrics['min_distance'] < requirements['min_distance']:
        meets_requirements = False
        score -= 10.0  # Heavy penalty
    else:
        score += 1.0

    return meets_requirements, score


def tune_pid_parameters():
    """
    Tune PID parameters through iterative testing.

    Returns:
        dict: Best PID parameters
    """
    # Load base configuration
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    # Test different PID parameter combinations
    best_score = -999999
    best_params = None
    best_metrics = None

    print("Starting PID parameter tuning...")

    # Speed PID candidates (prioritize responsiveness for cruise mode)
    speed_candidates = [
        {'kp': 2.0, 'ki': 0.3, 'kd': 0.1},
        {'kp': 2.5, 'ki': 0.4, 'kd': 0.15},
        {'kp': 3.0, 'ki': 0.5, 'kd': 0.2},
        {'kp': 1.5, 'ki': 0.2, 'kd': 0.05},
        {'kp': 2.2, 'ki': 0.35, 'kd': 0.12},
    ]

    # Distance PID candidates (prioritize smoothness for follow mode)
    distance_candidates = [
        {'kp': 0.8, 'ki': 0.1, 'kd': 0.3},
        {'kp': 1.0, 'ki': 0.15, 'kd': 0.4},
        {'kp': 1.2, 'ki': 0.2, 'kd': 0.5},
        {'kp': 0.6, 'ki': 0.08, 'kd': 0.25},
        {'kp': 0.9, 'ki': 0.12, 'kd': 0.35},
    ]

    test_count = 0
    total_tests = len(speed_candidates) * len(distance_candidates)

    for speed_pid in speed_candidates:
        for distance_pid in distance_candidates:
            test_count += 1

            # Create test configuration
            config = base_config.copy()
            config['pid_speed'] = speed_pid
            config['pid_distance'] = distance_pid

            # Run test simulation
            try:
                _, metrics = run_test_simulation(config)

                # Evaluate performance
                meets_req, score = evaluate_performance(metrics)

                print(f"\nTest {test_count}/{total_tests}:")
                print(f"  Speed PID: kp={speed_pid['kp']}, ki={speed_pid['ki']}, kd={speed_pid['kd']}")
                print(f"  Distance PID: kp={distance_pid['kp']}, ki={distance_pid['ki']}, kd={distance_pid['kd']}")
                print(f"  Rise time: {metrics['rise_time']:.2f}s")
                print(f"  Overshoot: {metrics['overshoot_pct']:.2f}%")
                print(f"  Speed SS error: {metrics['speed_ss_error']:.3f} m/s")
                print(f"  Distance SS error: {metrics['distance_ss_error']:.2f} m")
                print(f"  Min distance: {metrics['min_distance']:.2f} m")
                print(f"  Score: {score:.2f}, Meets requirements: {meets_req}")

                if score > best_score:
                    best_score = score
                    best_params = {
                        'pid_speed': speed_pid,
                        'pid_distance': distance_pid
                    }
                    best_metrics = metrics

            except Exception as e:
                print(f"Test {test_count} failed: {e}")

    print("\n" + "="*60)
    print("Tuning complete!")
    print("="*60)
    print("\nBest parameters:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']}, "
          f"ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']}, "
          f"ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print(f"\nBest metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance SS error: {best_metrics['distance_ss_error']:.2f} m (target: <2m)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m)")

    return best_params


def save_tuning_results(params):
    """
    Save tuned parameters to YAML file.

    Args:
        params (dict): Best PID parameters
    """
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(params, f, default_flow_style=False, sort_keys=False)

    print("\nTuned parameters saved to tuning_results.yaml")


if __name__ == '__main__':
    # Tune PID parameters
    best_params = tune_pid_parameters()

    # Save results
    save_tuning_results(best_params)

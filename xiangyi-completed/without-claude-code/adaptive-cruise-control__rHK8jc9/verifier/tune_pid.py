"""PID Parameter Tuning Script for ACC System"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl
from pid_controller import PIDController


def simulate_with_params(config, sensor_data, speed_params, distance_params):
    """
    Run simulation with given PID parameters.

    Args:
        config: Configuration dictionary
        sensor_data: DataFrame with sensor data
        speed_params: (kp, ki, kd) for speed controller
        distance_params: (kp, ki, kd) for distance controller

    Returns:
        dict: Performance metrics
    """
    # Update config with test parameters
    config['pid_speed'] = {'kp': speed_params[0], 'ki': speed_params[1], 'kd': speed_params[2]}
    config['pid_distance'] = {'kp': distance_params[0], 'ki': distance_params[1], 'kd': distance_params[2]}

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation variables
    dt = config['simulation']['dt']
    ego_speed = 0.0
    results = []

    # Run simulation
    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed = max(0, ego_speed + accel_cmd * dt)

        results.append({
            'time': row['time'],
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance
        })

    results_df = pd.DataFrame(results)

    # Calculate performance metrics
    metrics = calculate_metrics(results_df, config['acc_settings']['set_speed'])

    return metrics, results_df


def calculate_metrics(results_df, set_speed):
    """Calculate performance metrics from simulation results."""
    metrics = {}

    # Speed control metrics (cruise phase before lead vehicle appears)
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    if len(cruise_data) > 0:
        # Rise time: time to reach 90% of set_speed
        target_90 = 0.9 * set_speed
        rise_mask = cruise_data['ego_speed'] >= target_90
        if rise_mask.any():
            metrics['rise_time'] = cruise_data[rise_mask].iloc[0]['time']
        else:
            metrics['rise_time'] = 999

        # Overshoot: maximum speed beyond set_speed
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_percent'] = max(0, (max_speed - set_speed) / set_speed * 100)

        # Steady-state error in cruise (last 20% of cruise phase)
        cruise_end_idx = int(len(cruise_data) * 0.8)
        if cruise_end_idx < len(cruise_data):
            ss_cruise = cruise_data.iloc[cruise_end_idx:]
            metrics['speed_ss_error'] = abs(ss_cruise['ego_speed'].mean() - set_speed)
        else:
            metrics['speed_ss_error'] = abs(cruise_data['ego_speed'].iloc[-1] - set_speed)
    else:
        metrics['rise_time'] = 999
        metrics['overshoot_percent'] = 999
        metrics['speed_ss_error'] = 999

    # Distance control metrics (follow phase)
    follow_data = results_df[results_df['mode'] == 'follow'].copy()

    if len(follow_data) > 0:
        # Steady-state distance error (last 30% of follow phase)
        follow_end_idx = int(len(follow_data) * 0.7)
        if follow_end_idx < len(follow_data):
            ss_follow = follow_data.iloc[follow_end_idx:]
            metrics['distance_ss_error'] = abs(ss_follow['distance_error'].mean())
        else:
            metrics['distance_ss_error'] = abs(follow_data['distance_error'].mean())

        # Minimum distance maintained
        metrics['min_distance'] = follow_data['distance'].min()
    else:
        metrics['distance_ss_error'] = 0
        metrics['min_distance'] = 999

    # Emergency braking events
    metrics['emergency_events'] = (results_df['mode'] == 'emergency').sum()

    return metrics


def grid_search_speed_pid():
    """Grid search for speed PID parameters."""
    print("Tuning Speed PID Controller...")

    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Fixed distance PID (will tune separately)
    distance_params = (0.3, 0.05, 0.2)

    # Grid search parameters
    kp_values = [0.5, 1.0, 1.5, 2.0, 2.5]
    ki_values = [0.0, 0.05, 0.1, 0.2]
    kd_values = [0.0, 0.1, 0.2, 0.5]

    best_score = float('inf')
    best_params = None

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                speed_params = (kp, ki, kd)
                metrics, _ = simulate_with_params(config, sensor_data, speed_params, distance_params)

                # Objective: minimize weighted sum of errors
                score = (
                    5.0 * max(0, metrics['rise_time'] - 10) +  # Penalty if rise time > 10s
                    10.0 * max(0, metrics['overshoot_percent'] - 5) +  # Penalty if overshoot > 5%
                    20.0 * max(0, metrics['speed_ss_error'] - 0.5) +  # Penalty if ss error > 0.5
                    metrics['speed_ss_error'] * 2 +  # General error term
                    metrics['rise_time'] * 0.1  # Prefer faster response
                )

                if score < best_score:
                    best_score = score
                    best_params = speed_params
                    print(f"  Better params found: kp={kp:.2f}, ki={ki:.2f}, kd={kd:.2f}")
                    print(f"    Rise time: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot_percent']:.2f}%, SS error: {metrics['speed_ss_error']:.3f}")

    print(f"\nBest Speed PID: kp={best_params[0]}, ki={best_params[1]}, kd={best_params[2]}")
    return best_params


def grid_search_distance_pid(speed_params):
    """Grid search for distance PID parameters."""
    print("\nTuning Distance PID Controller...")

    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Grid search parameters - focus on higher kp for better tracking
    kp_values = [0.8, 1.0, 1.5, 2.0, 2.5, 3.0]
    ki_values = [0.0, 0.01, 0.02, 0.05]
    kd_values = [0.5, 1.0, 1.5, 2.0, 2.5]

    best_score = float('inf')
    best_params = None

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                distance_params = (kp, ki, kd)
                metrics, _ = simulate_with_params(config, sensor_data, speed_params, distance_params)

                # Objective: minimize distance error while maintaining safety
                score = (
                    500.0 * max(0, 5 - metrics['min_distance']) +  # Very heavy penalty if min distance < 5m
                    20.0 * max(0, metrics['distance_ss_error'] - 2) +  # Penalty if ss error > 2m
                    metrics['distance_ss_error'] * 3 +  # General distance error
                    200.0 * metrics['emergency_events']  # Heavy penalty for emergency events
                )

                if score < best_score:
                    best_score = score
                    best_params = distance_params
                    print(f"  Better params found: kp={kp:.2f}, ki={ki:.2f}, kd={kd:.2f}")
                    print(f"    Min distance: {metrics['min_distance']:.2f}m, SS error: {metrics['distance_ss_error']:.3f}m, Emergency events: {metrics['emergency_events']}")

    print(f"\nBest Distance PID: kp={best_params[0]}, ki={best_params[1]}, kd={best_params[2]}")
    return best_params


def main():
    """Main tuning procedure."""
    print("=" * 60)
    print("PID Parameter Tuning for ACC System")
    print("=" * 60)

    # Tune speed controller first
    speed_params = grid_search_speed_pid()

    # Tune distance controller with optimized speed controller
    distance_params = grid_search_distance_pid(speed_params)

    # Save results
    tuning_results = {
        'pid_speed': {
            'kp': float(speed_params[0]),
            'ki': float(speed_params[1]),
            'kd': float(speed_params[2])
        },
        'pid_distance': {
            'kp': float(distance_params[0]),
            'ki': float(distance_params[1]),
            'kd': float(distance_params[2])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\n" + "=" * 60)
    print("Tuning complete! Results saved to tuning_results.yaml")
    print("=" * 60)
    print(yaml.dump(tuning_results, default_flow_style=False))


if __name__ == '__main__':
    main()

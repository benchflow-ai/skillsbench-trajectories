"""PID tuning script for ACC system."""

import numpy as np
import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_params, distance_params, sensor_data, config, dt):
    """Run simulation with given PID parameters.

    Args:
        speed_params: (kp, ki, kd) for speed controller
        distance_params: (kp, ki, kd) for distance controller
        sensor_data: DataFrame with sensor measurements
        config: Configuration dictionary
        dt: Time step

    Returns:
        dict: Performance metrics
    """
    # Update config with tuning parameters
    config['pid_speed'] = {'kp': speed_params[0], 'ki': speed_params[1], 'kd': speed_params[2]}
    config['pid_distance'] = {'kp': distance_params[0], 'ki': distance_params[1], 'kd': distance_params[2]}

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize state
    ego_speed = 0.0
    results = []

    # Simulate
    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed (simple integration)
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)  # No negative speeds

        results.append({
            'time': row['time'],
            'ego_speed': ego_speed,
            'accel_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance
        })

    results_df = pd.DataFrame(results)

    # Calculate metrics
    metrics = calculate_metrics(results_df, config['acc_settings']['set_speed'])

    return metrics, results_df


def calculate_metrics(results_df, set_speed):
    """Calculate performance metrics from simulation results.

    Args:
        results_df: Simulation results
        set_speed: Target cruise speed

    Returns:
        dict: Performance metrics
    """
    metrics = {}

    # Speed metrics (cruise mode only)
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    if len(cruise_data) > 0:
        # Rise time: time to reach 90% of set speed
        target_90 = 0.9 * set_speed
        rising = cruise_data[cruise_data['ego_speed'] < target_90]
        if len(rising) > 0:
            metrics['rise_time'] = rising['time'].iloc[-1]
        else:
            metrics['rise_time'] = 0.0

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = max(0, (max_speed - set_speed) / set_speed * 100)

        # Steady-state error (last 20% of cruise period)
        steady_idx = int(len(cruise_data) * 0.8)
        if steady_idx < len(cruise_data):
            steady_state = cruise_data.iloc[steady_idx:]
            metrics['steady_state_error_speed'] = abs(steady_state['ego_speed'].mean() - set_speed)
        else:
            metrics['steady_state_error_speed'] = abs(cruise_data['ego_speed'].iloc[-1] - set_speed)
    else:
        metrics['rise_time'] = float('inf')
        metrics['overshoot_pct'] = 0
        metrics['steady_state_error_speed'] = float('inf')

    # Distance metrics (follow mode only)
    follow_data = results_df[results_df['mode'] == 'follow'].copy()

    if len(follow_data) > 0 and follow_data['distance_error'].notna().any():
        # Steady-state distance error (last 20% of follow period)
        steady_idx = int(len(follow_data) * 0.8)
        if steady_idx < len(follow_data):
            steady_state = follow_data.iloc[steady_idx:]
            valid_errors = steady_state['distance_error'].dropna()
            if len(valid_errors) > 0:
                metrics['steady_state_error_distance'] = abs(valid_errors.mean())
            else:
                metrics['steady_state_error_distance'] = 0
        else:
            metrics['steady_state_error_distance'] = abs(follow_data['distance_error'].iloc[-1])

        # Minimum distance
        valid_distances = follow_data['distance'].dropna()
        if len(valid_distances) > 0:
            metrics['min_distance'] = valid_distances.min()
        else:
            metrics['min_distance'] = float('inf')
    else:
        metrics['steady_state_error_distance'] = 0
        metrics['min_distance'] = float('inf')

    return metrics


def evaluate_params(speed_params, distance_params, sensor_data, config, dt, requirements):
    """Evaluate PID parameters against requirements.

    Returns:
        float: Cost function value (lower is better)
    """
    metrics, _ = simulate_with_params(speed_params, distance_params, sensor_data, config, dt)

    # Calculate cost based on requirement violations
    cost = 0

    # Speed rise time penalty
    if metrics['rise_time'] > requirements['max_rise_time']:
        cost += (metrics['rise_time'] - requirements['max_rise_time']) * 10

    # Overshoot penalty
    if metrics['overshoot_pct'] > requirements['max_overshoot_pct']:
        cost += (metrics['overshoot_pct'] - requirements['max_overshoot_pct']) * 5

    # Speed steady-state error penalty
    if metrics['steady_state_error_speed'] > requirements['max_speed_ss_error']:
        cost += (metrics['steady_state_error_speed'] - requirements['max_speed_ss_error']) * 20

    # Distance steady-state error penalty
    if metrics['steady_state_error_distance'] > requirements['max_distance_ss_error']:
        cost += (metrics['steady_state_error_distance'] - requirements['max_distance_ss_error']) * 10

    # Minimum distance penalty
    if metrics['min_distance'] < requirements['min_safe_distance']:
        cost += (requirements['min_safe_distance'] - metrics['min_distance']) * 50

    # Add base cost for tracking errors
    cost += metrics['steady_state_error_speed'] * 2
    cost += metrics['steady_state_error_distance'] * 1
    cost += metrics['overshoot_pct'] * 0.5

    return cost


def grid_search_tuning():
    """Perform grid search to find optimal PID parameters."""
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')

    dt = config['simulation']['dt']

    # Requirements
    requirements = {
        'max_rise_time': 10.0,
        'max_overshoot_pct': 5.0,
        'max_speed_ss_error': 0.5,
        'max_distance_ss_error': 2.0,
        'min_safe_distance': 5.0
    }

    print("Tuning PID parameters...")
    print("=" * 60)

    # Grid search ranges
    # Speed controller: needs higher gains for fast response
    speed_kp_range = [0.5, 1.0, 1.5, 2.0, 2.5]
    speed_ki_range = [0.05, 0.1, 0.15, 0.2]
    speed_kd_range = [0.0, 0.1, 0.2, 0.3]

    # Distance controller: needs moderate gains for smooth following
    distance_kp_range = [0.3, 0.5, 0.7, 1.0, 1.2]
    distance_ki_range = [0.01, 0.05, 0.1, 0.15]
    distance_kd_range = [0.1, 0.2, 0.3, 0.5]

    best_cost = float('inf')
    best_speed_params = None
    best_distance_params = None
    best_metrics = None

    # First optimize speed controller
    print("\nPhase 1: Optimizing speed controller...")
    for kp in speed_kp_range:
        for ki in speed_ki_range:
            for kd in speed_kd_range:
                speed_params = (kp, ki, kd)
                # Use default distance params for now
                distance_params = (0.5, 0.05, 0.2)

                cost = evaluate_params(speed_params, distance_params, sensor_data, config, dt, requirements)

                if cost < best_cost:
                    best_cost = cost
                    best_speed_params = speed_params
                    best_distance_params = distance_params
                    metrics, _ = simulate_with_params(speed_params, distance_params, sensor_data, config, dt)
                    best_metrics = metrics

    print(f"Best speed params: kp={best_speed_params[0]}, ki={best_speed_params[1]}, kd={best_speed_params[2]}")
    print(f"Cost: {best_cost:.2f}")

    # Now optimize distance controller with best speed params
    print("\nPhase 2: Optimizing distance controller...")
    for kp in distance_kp_range:
        for ki in distance_ki_range:
            for kd in distance_kd_range:
                distance_params = (kp, ki, kd)

                cost = evaluate_params(best_speed_params, distance_params, sensor_data, config, dt, requirements)

                if cost < best_cost:
                    best_cost = cost
                    best_distance_params = distance_params
                    metrics, _ = simulate_with_params(best_speed_params, distance_params, sensor_data, config, dt)
                    best_metrics = metrics

    print(f"Best distance params: kp={best_distance_params[0]}, ki={best_distance_params[1]}, kd={best_distance_params[2]}")
    print(f"Final cost: {best_cost:.2f}")

    # Display final metrics
    print("\n" + "=" * 60)
    print("Final Performance Metrics:")
    print("=" * 60)
    print(f"Rise time: {best_metrics['rise_time']:.2f}s (requirement: <10s)")
    print(f"Overshoot: {best_metrics['overshoot_pct']:.2f}% (requirement: <5%)")
    print(f"Speed steady-state error: {best_metrics['steady_state_error_speed']:.3f} m/s (requirement: <0.5 m/s)")
    print(f"Distance steady-state error: {best_metrics['steady_state_error_distance']:.3f} m (requirement: <2m)")
    print(f"Minimum distance: {best_metrics['min_distance']:.2f} m (requirement: >5m)")

    # Save results
    tuning_results = {
        'pid_speed': {
            'kp': float(best_speed_params[0]),
            'ki': float(best_speed_params[1]),
            'kd': float(best_speed_params[2])
        },
        'pid_distance': {
            'kp': float(best_distance_params[0]),
            'ki': float(best_distance_params[1]),
            'kd': float(best_distance_params[2])
        }
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")

    return best_speed_params, best_distance_params, best_metrics


if __name__ == '__main__':
    grid_search_tuning()

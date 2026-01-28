"""PID parameter tuning script for ACC system."""

import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_gains, distance_gains, sensor_data, config):
    """Run simulation with given PID parameters.

    Args:
        speed_gains: (kp, ki, kd) for speed controller
        distance_gains: (kp, ki, kd) for distance controller
        sensor_data: DataFrame with sensor data
        config: Base configuration dict

    Returns:
        dict: Performance metrics
    """
    # Update config with new gains
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Simulation variables with position tracking
    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    prev_lead_speed = None
    results = []
    min_distance_observed = float('inf')

    for _, row in sensor_data.iterrows():
        time = row['time']
        lead_speed_csv = row['lead_speed'] if pd.notna(row['lead_speed']) else None

        # Handle lead vehicle position tracking
        if lead_speed_csv is not None:
            if prev_lead_speed is None:
                # Lead vehicle just appeared
                initial_distance = row['distance']
                lead_position = ego_position + initial_distance
            else:
                # Update lead position
                lead_position += prev_lead_speed * dt

            distance = lead_position - ego_position
            lead_speed = lead_speed_csv
            prev_lead_speed = lead_speed_csv
        else:
            distance = None
            lead_speed = None
            lead_position = None
            prev_lead_speed = None

        # Compute control
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego vehicle
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_position += ego_speed * dt

        # Track minimum distance
        if distance is not None:
            min_distance_observed = min(min_distance_observed, distance)

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance
        })

    results_df = pd.DataFrame(results)

    # Calculate performance metrics
    metrics = calculate_metrics(results_df, config['acc_settings']['set_speed'], min_distance_observed)

    return metrics, results_df


def calculate_metrics(results_df, set_speed, min_distance_observed):
    """Calculate performance metrics from simulation results.

    Args:
        results_df: DataFrame with simulation results
        set_speed: Target cruise speed (m/s)
        min_distance_observed: Minimum distance observed during simulation

    Returns:
        dict: Performance metrics
    """
    metrics = {}

    # Speed metrics (cruise phase before lead vehicle appears)
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    if len(cruise_data) > 0:
        # Find when speed reaches 90% of set speed (rise time)
        speed_90_percent = 0.9 * set_speed
        rise_time_rows = cruise_data[cruise_data['ego_speed'] >= speed_90_percent]

        if len(rise_time_rows) > 0:
            metrics['rise_time'] = rise_time_rows.iloc[0]['time']
        else:
            metrics['rise_time'] = None

        # Maximum overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot = max(0, max_speed - set_speed)
        metrics['overshoot_percent'] = (overshoot / set_speed) * 100

        # Steady-state error (last 5 seconds of cruise phase)
        steady_state_data = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 5.0]
        if len(steady_state_data) > 0:
            metrics['speed_steady_state_error'] = abs(steady_state_data['ego_speed'].mean() - set_speed)
        else:
            metrics['speed_steady_state_error'] = None
    else:
        metrics['rise_time'] = None
        metrics['overshoot_percent'] = None
        metrics['speed_steady_state_error'] = None

    # Distance metrics (follow phase)
    follow_data = results_df[(results_df['mode'] == 'follow') & results_df['distance_error'].notna()].copy()

    if len(follow_data) > 0:
        # Distance steady-state error (last 30 seconds)
        steady_state_follow = follow_data[follow_data['time'] >= follow_data['time'].max() - 30.0]
        if len(steady_state_follow) > 0:
            metrics['distance_steady_state_error'] = abs(steady_state_follow['distance_error'].mean())
        else:
            metrics['distance_steady_state_error'] = None
    else:
        metrics['distance_steady_state_error'] = None

    # Minimum distance
    metrics['min_distance'] = min_distance_observed

    return metrics


def grid_search_tuning():
    """Perform grid search to find optimal PID parameters."""
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')

    print("Starting PID parameter tuning...")
    print(f"Target: Rise time < 10s, Overshoot < 5%, Speed SS error < 0.5 m/s")
    print(f"Target: Distance SS error < 2m, Min distance > 5m\n")

    # Grid search ranges (kp in (0,10), ki in [0,5), kd in [0,5))
    speed_kp_range = [0.8, 1.0, 1.2, 1.5]
    speed_ki_range = [0.0, 0.02, 0.05, 0.1]
    speed_kd_range = [0.0, 0.2, 0.5]

    distance_kp_range = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    distance_ki_range = [0.02, 0.05, 0.1, 0.2, 0.3]
    distance_kd_range = [1.0, 1.5, 2.0, 2.5, 3.0]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    # First, tune speed controller with fixed distance gains
    print("Phase 1: Tuning speed controller...")
    temp_distance_gains = (2.5, 0.1, 2.0)

    for kp in speed_kp_range:
        for ki in speed_ki_range:
            for kd in speed_kd_range:
                speed_gains = (kp, ki, kd)
                metrics, _ = simulate_with_params(speed_gains, temp_distance_gains, sensor_data, config.copy())

                # Score based on speed performance
                if metrics['rise_time'] is None or metrics['speed_steady_state_error'] is None:
                    continue

                score = 0
                score += max(0, metrics['rise_time'] - 10.0) * 10  # Penalty for slow rise
                score += max(0, metrics['overshoot_percent'] - 5.0) * 10  # Penalty for overshoot
                score += max(0, metrics['speed_steady_state_error'] - 0.5) * 20  # Penalty for SS error
                score += metrics['rise_time']  # Prefer faster rise times
                score += metrics['overshoot_percent']  # Prefer less overshoot

                if score < best_score:
                    best_score = score
                    best_speed_gains = speed_gains
                    best_speed_metrics = metrics

    print(f"Best speed gains: kp={best_speed_gains[0]:.2f}, ki={best_speed_gains[1]:.2f}, kd={best_speed_gains[2]:.2f}")
    print(f"  Rise time: {best_speed_metrics['rise_time']:.2f}s")
    print(f"  Overshoot: {best_speed_metrics['overshoot_percent']:.2f}%")
    print(f"  Speed SS error: {best_speed_metrics['speed_steady_state_error']:.3f} m/s\n")

    # Phase 2: Tune distance controller with optimized speed gains
    print("Phase 2: Tuning distance controller...")
    best_score = float('inf')

    for kp in distance_kp_range:
        for ki in distance_ki_range:
            for kd in distance_kd_range:
                distance_gains = (kp, ki, kd)
                metrics, _ = simulate_with_params(best_speed_gains, distance_gains, sensor_data, config.copy())

                # Score based on distance performance and maintaining speed performance
                if (metrics['distance_steady_state_error'] is None or
                    metrics['speed_steady_state_error'] is None):
                    continue

                score = 0
                score += max(0, metrics['distance_steady_state_error'] - 2.0) * 30
                score += max(0, 5.0 - metrics['min_distance']) * 100  # Heavy penalty if min distance < 5m
                score += max(0, metrics['speed_steady_state_error'] - 0.5) * 10
                score += abs(metrics['distance_steady_state_error'])  # Prefer smaller distance errors

                if score < best_score:
                    best_score = score
                    best_distance_gains = distance_gains
                    best_metrics = metrics

    print(f"Best distance gains: kp={best_distance_gains[0]:.2f}, ki={best_distance_gains[1]:.2f}, kd={best_distance_gains[2]:.2f}")
    if best_metrics['distance_steady_state_error'] is not None:
        print(f"  Distance SS error: {best_metrics['distance_steady_state_error']:.2f} m")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m\n")

    # Final simulation with best parameters
    print("Running final simulation with optimized parameters...")
    final_metrics, final_results = simulate_with_params(best_speed_gains, best_distance_gains, sensor_data, config.copy())

    print("\nFinal Performance Metrics:")
    print(f"  Rise time: {final_metrics['rise_time']:.2f}s (target: <10s) {'✓' if final_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot: {final_metrics['overshoot_percent']:.2f}% (target: <5%) {'✓' if final_metrics['overshoot_percent'] < 5 else '✗'}")
    print(f"  Speed SS error: {final_metrics['speed_steady_state_error']:.3f} m/s (target: <0.5) {'✓' if final_metrics['speed_steady_state_error'] < 0.5 else '✗'}")
    if final_metrics['distance_steady_state_error'] is not None:
        print(f"  Distance SS error: {final_metrics['distance_steady_state_error']:.2f} m (target: <2m) {'✓' if final_metrics['distance_steady_state_error'] < 2 else '✗'}")
    print(f"  Min distance: {final_metrics['min_distance']:.2f} m (target: >5m) {'✓' if final_metrics['min_distance'] > 5 else '✗'}")

    # Save results
    tuning_results = {
        'pid_speed': {
            'kp': float(best_speed_gains[0]),
            'ki': float(best_speed_gains[1]),
            'kd': float(best_speed_gains[2])
        },
        'pid_distance': {
            'kp': float(best_distance_gains[0]),
            'ki': float(best_distance_gains[1]),
            'kd': float(best_distance_gains[2])
        }
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")


if __name__ == '__main__':
    grid_search_tuning()

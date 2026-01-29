"""PID Parameter Tuning for ACC System."""

import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


def calculate_metrics(results_df, set_speed=30.0):
    """
    Calculate performance metrics from simulation results.

    Args:
        results_df: DataFrame with simulation results
        set_speed: Target cruise speed

    Returns:
        dict: Performance metrics
    """
    metrics = {}

    # Extract cruise mode data for speed control analysis
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()

    if len(cruise_data) > 0:
        # Rise time: Time to reach 90% of setpoint
        target_speed = 0.9 * set_speed
        rise_data = cruise_data[cruise_data['ego_speed'] >= target_speed]
        if len(rise_data) > 0:
            metrics['rise_time'] = rise_data.iloc[0]['time']
        else:
            metrics['rise_time'] = 999.0  # Never reached

        # Overshoot: Maximum value above setpoint
        max_speed = cruise_data['ego_speed'].max()
        if max_speed > set_speed:
            metrics['overshoot'] = (max_speed - set_speed) / set_speed * 100
        else:
            metrics['overshoot'] = 0.0

        # Steady-state error: Last 20% of cruise mode
        steady_start = int(len(cruise_data) * 0.8)
        if steady_start < len(cruise_data):
            steady_speeds = cruise_data.iloc[steady_start:]['ego_speed']
            metrics['steady_state_error'] = abs(steady_speeds.mean() - set_speed)
        else:
            metrics['steady_state_error'] = abs(cruise_data.iloc[-1]['ego_speed'] - set_speed)
    else:
        metrics['rise_time'] = 999.0
        metrics['overshoot'] = 0.0
        metrics['steady_state_error'] = 999.0

    # Distance control metrics (follow mode)
    follow_data = results_df[results_df['mode'] == 'follow'].copy()
    if len(follow_data) > 0:
        # Convert empty strings to NaN for proper handling
        follow_data['distance_error'] = pd.to_numeric(follow_data['distance_error'], errors='coerce')
        follow_data['distance'] = pd.to_numeric(follow_data['distance'], errors='coerce')

        # Remove NaN values
        valid_distance_errors = follow_data['distance_error'].dropna()
        valid_distances = follow_data['distance'].dropna()

        if len(valid_distance_errors) > 0:
            metrics['mean_distance_error'] = abs(valid_distance_errors.mean())
        else:
            metrics['mean_distance_error'] = 0.0

        if len(valid_distances) > 0:
            metrics['min_distance'] = valid_distances.min()
        else:
            metrics['min_distance'] = 999.0
    else:
        metrics['mean_distance_error'] = 0.0
        metrics['min_distance'] = 999.0

    return metrics


def calculate_score(metrics):
    """
    Calculate composite performance score (lower is better).

    Args:
        metrics: Dictionary of performance metrics

    Returns:
        float: Performance score
    """
    score = 0.0

    # Rise time penalty (target: < 10s)
    if metrics['rise_time'] > 10:
        score += (metrics['rise_time'] - 10) ** 2 * 5

    # Overshoot penalty (target: < 5%)
    if metrics['overshoot'] > 5:
        score += (metrics['overshoot'] - 5) ** 2 * 10

    # Steady-state error penalty (target: < 0.5 m/s)
    score += abs(metrics['steady_state_error']) * 100

    # Distance error penalty (target: < 2m)
    if metrics['mean_distance_error'] > 2:
        score += (metrics['mean_distance_error'] - 2) ** 2 * 20

    # Minimum distance penalty (must be > 5m)
    if metrics['min_distance'] < 5:
        score += (5 - metrics['min_distance']) ** 2 * 50

    return score


def simulate_with_params(kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist):
    """
    Run simulation with given PID parameters.

    Returns:
        DataFrame: Simulation results
    """
    # Load base config
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Update with test parameters
    config['pid_speed'] = {'kp': kp_speed, 'ki': ki_speed, 'kd': kd_speed}
    config['pid_distance'] = {'kp': kp_dist, 'ki': ki_dist, 'kd': kd_dist}

    # Load sensor data
    sensor_df = pd.read_csv('sensor_data.csv')

    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Run simulation
    ego_speed = 0.0
    results = []

    for idx, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else ''
        })

        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)

    return pd.DataFrame(results)


def tune_pid_parameters():
    """
    Tune PID parameters using grid search.

    Returns:
        dict: Best parameters
    """
    print("Starting PID parameter tuning...")

    # Define search space with emphasis on derivative term to reduce overshoot
    # Speed control: kp in (0,10), ki in [0,5), kd in [0,5)
    kp_speed_values = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    ki_speed_values = [0.0, 0.05, 0.1, 0.15, 0.2]
    kd_speed_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]  # Higher Kd to reduce overshoot

    # Distance control: kp in (0,10), ki in [0,5), kd in [0,5)
    kp_dist_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ki_dist_values = [0.0, 0.02, 0.05, 0.08, 0.1]
    kd_dist_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    best_score = float('inf')
    best_params = None
    iteration = 0

    # Grid search
    for kp_s in kp_speed_values:
        for ki_s in ki_speed_values:
            for kd_s in kd_speed_values:
                for kp_d in kp_dist_values:
                    for ki_d in ki_dist_values:
                        for kd_d in kd_dist_values:
                            iteration += 1

                            # Run simulation
                            results_df = simulate_with_params(
                                kp_s, ki_s, kd_s, kp_d, ki_d, kd_d
                            )

                            # Calculate metrics
                            metrics = calculate_metrics(results_df)
                            score = calculate_score(metrics)

                            # Check hard constraints first
                            if metrics['overshoot'] > 5.0:
                                continue  # Skip configurations that violate overshoot constraint

                            if score < best_score:
                                best_score = score
                                best_params = {
                                    'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                    'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
                                }
                                print(f"Iteration {iteration}: New best score = {score:.2f}")
                                print(f"  Speed PID: Kp={kp_s}, Ki={ki_s}, Kd={kd_s}")
                                print(f"  Dist PID:  Kp={kp_d}, Ki={ki_d}, Kd={kd_d}")
                                print(f"  Metrics: Rise={metrics['rise_time']:.1f}s, Overshoot={metrics['overshoot']:.2f}%, SSE={metrics['steady_state_error']:.3f}")

    if best_params is None:
        print("WARNING: No parameters found that meet overshoot constraint. Using fallback.")
        best_params = {
            'pid_speed': {'kp': 2.0, 'ki': 0.1, 'kd': 2.0},
            'pid_distance': {'kp': 1.5, 'ki': 0.05, 'kd': 2.0}
        }

    print(f"\nTuning completed after {iteration} iterations")
    print(f"Best score: {best_score:.2f}")
    print(f"Best parameters: {best_params}")

    return best_params


def main():
    """Main tuning function."""
    # Tune parameters
    best_params = tune_pid_parameters()

    # Save to YAML
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_params, f, default_flow_style=False)

    print("\nTuned parameters saved to tuning_results.yaml")

    # Run final simulation with best parameters
    print("\nRunning final validation simulation...")
    results_df = simulate_with_params(
        best_params['pid_speed']['kp'],
        best_params['pid_speed']['ki'],
        best_params['pid_speed']['kd'],
        best_params['pid_distance']['kp'],
        best_params['pid_distance']['ki'],
        best_params['pid_distance']['kd']
    )

    metrics = calculate_metrics(results_df)
    print("\nFinal performance metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.3f}")


if __name__ == '__main__':
    main()

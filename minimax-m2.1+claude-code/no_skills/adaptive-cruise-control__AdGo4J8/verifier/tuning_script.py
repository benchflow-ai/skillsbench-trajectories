"""PID tuning script for ACC system."""

import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def run_simulation_eval(config: dict, sensor_df: pd.DataFrame, dt: float) -> dict:
    """Run simulation and return metrics for evaluation."""
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    speeds = []
    distances = []
    modes = []
    distance_errors = []

    for idx, row in sensor_df.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        acc_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed = max(0.0, ego_speed + acc_cmd * dt)
        speeds.append(ego_speed)
        distances.append(distance if distance else np.nan)
        modes.append(mode)
        distance_errors.append(distance_error if distance_error else np.nan)

    set_speed = config['acc_settings']['set_speed']
    speeds = np.array(speeds)

    # Calculate metrics
    # Rise time
    target_90 = 0.9 * set_speed
    rise_time_idx = np.argmax(speeds >= target_90)
    rise_time = sensor_df['time'].iloc[rise_time_idx] if speeds[rise_time_idx] >= target_90 else 150.0

    # Overshoot
    max_speed = speeds.max()
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Speed steady-state error (last 50 seconds)
    steady_idx = int(500)  # t >= 100s
    speed_steady_error = abs(set_speed - speeds[steady_idx:].mean())

    # Distance metrics
    follow_mask = np.array([m == 'follow' for m in modes])
    if follow_mask.any():
        valid_distances = np.array(distances)[follow_mask]
        min_distance = np.nanmin(valid_distances)
        distance_errors_arr = np.array(distance_errors)
        valid_errors = distance_errors_arr[follow_mask & ~np.isnan(distance_errors_arr)]
        if len(valid_errors) > 0:
            distance_steady_error = np.abs(valid_errors[-200:]).mean() if len(valid_errors) > 200 else np.abs(valid_errors).mean()
        else:
            distance_steady_error = 0.0
    else:
        min_distance = 10.0
        distance_steady_error = 0.0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_steady_error': speed_steady_error,
        'min_distance': min_distance,
        'distance_steady_error': distance_steady_error,
        'speeds': speeds
    }


def evaluate_gains(gains: dict, config: dict, sensor_df: pd.DataFrame, dt: float) -> float:
    """Evaluate PID gains and return a cost score."""
    # Update config with gains
    config['pid_speed'] = {'kp': gains['kp_speed'], 'ki': gains['ki_speed'], 'kd': gains['kd_speed']}
    config['pid_distance'] = {'kp': gains['kp_distance'], 'ki': gains['ki_distance'], 'kd': gains['kd_distance']}

    metrics = run_simulation_eval(config, sensor_df, dt)

    # Calculate cost (lower is better)
    # Weights for different objectives
    cost = 0.0

    # Rise time penalty (< 10s target)
    if metrics['rise_time'] > 10:
        cost += (metrics['rise_time'] - 10) * 10

    # Overshoot penalty (< 5% target)
    if metrics['overshoot'] > 5:
        cost += (metrics['overshoot'] - 5) * 20

    # Speed steady-state error penalty (< 0.5 m/s target)
    if metrics['speed_steady_error'] > 0.5:
        cost += (metrics['speed_steady_error'] - 0.5) * 50

    # Min distance penalty (> 5m target)
    if metrics['min_distance'] < 5:
        cost += (5 - metrics['min_distance']) * 10

    # Distance steady-state error penalty (< 2m target)
    if metrics['distance_steady_error'] > 2:
        cost += (metrics['distance_steady_error'] - 2) * 5

    return cost, metrics


def grid_search_tuning(config_path: str, sensor_data_path: str, output_path: str):
    """Perform grid search for PID tuning."""
    config = load_config(config_path)
    sensor_df = pd.read_csv(sensor_data_path)
    dt = config.get('simulation', {}).get('dt', 0.1)

    # Grid search parameters
    kp_speed_range = np.linspace(0.5, 3.0, 6)
    ki_speed_range = np.linspace(0.01, 0.5, 5)
    kd_speed_range = np.linspace(0.0, 2.0, 5)

    kp_dist_range = np.linspace(0.1, 1.5, 6)
    ki_dist_range = np.linspace(0.01, 0.3, 5)
    kd_dist_range = np.linspace(0.0, 1.5, 5)

    best_cost = float('inf')
    best_gains = None
    best_metrics = None

    print("Starting grid search for PID tuning...")
    total_iterations = len(kp_speed_range) * len(ki_speed_range) * len(kd_speed_range) * \
                       len(kp_dist_range) * len(ki_dist_range) * len(kd_dist_range)
    print(f"Total iterations: {total_iterations}")

    iteration = 0
    for kp_s in kp_speed_range:
        for ki_s in ki_speed_range:
            for kd_s in kd_speed_range:
                for kp_d in kp_dist_range:
                    for ki_d in ki_dist_range:
                        for kd_d in kd_dist_range:
                            gains = {
                                'kp_speed': kp_s, 'ki_speed': ki_s, 'kd_speed': kd_s,
                                'kp_distance': kp_d, 'ki_distance': ki_d, 'kd_distance': kd_d
                            }
                            cost, metrics = evaluate_gains(gains, config.copy(), sensor_df, dt)

                            if cost < best_cost:
                                best_cost = cost
                                best_gains = gains
                                best_metrics = metrics

                            iteration += 1
                            if iteration % 500 == 0:
                                print(f"Progress: {iteration}/{total_iterations} ({(iteration/total_iterations)*100:.1f}%)")

    print(f"\nBest gains found:")
    print(f"Speed PID: kp={best_gains['kp_speed']:.3f}, ki={best_gains['ki_speed']:.3f}, kd={best_gains['kd_speed']:.3f}")
    print(f"Distance PID: kp={best_gains['kp_distance']:.3f}, ki={best_gains['ki_distance']:.3f}, kd={best_gains['kd_distance']:.3f}")
    print(f"\nBest metrics:")
    print(f"Rise time: {best_metrics['rise_time']:.2f}s")
    print(f"Overshoot: {best_metrics['overshoot']:.2f}%")
    print(f"Speed steady-state error: {best_metrics['speed_steady_error']:.4f} m/s")
    print(f"Min distance: {best_metrics['min_distance']:.2f}m")
    print(f"Distance steady-state error: {best_metrics['distance_steady_error']:.2f}m")
    print(f"Cost: {best_cost:.4f}")

    # Save results
    results = {
        'pid_speed': {
            'kp': round(best_gains['kp_speed'], 4),
            'ki': round(best_gains['ki_speed'], 4),
            'kd': round(best_gains['kd_speed'], 4)
        },
        'pid_distance': {
            'kp': round(best_gains['kp_distance'], 4),
            'ki': round(best_gains['ki_distance'], 4),
            'kd': round(best_gains['kd_distance'], 4)
        }
    }

    with open(output_path, 'w') as f:
        yaml.dump(results, f, default_flow_style=False)

    print(f"\nTuning results saved to {output_path}")
    return results


if __name__ == '__main__':
    grid_search_tuning(
        config_path='vehicle_params.yaml',
        sensor_data_path='sensor_data.csv',
        output_path='tuning_results.yaml'
    )

"""Final PID tuning with improved control logic."""

import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def run_simulation_eval(config: dict, sensor_df: pd.DataFrame, dt: float) -> dict:
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    speeds = []
    distances = []
    modes = []
    distance_errors = []

    for idx, row in sensor_df.iterrows():
        ref_ego_speed = row['ego_speed']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        acc_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt, ref_ego_speed)
        ego_speed = max(0.0, ego_speed + acc_cmd * dt)
        speeds.append(ego_speed)
        distances.append(distance if distance else np.nan)
        modes.append(mode)
        distance_errors.append(distance_error if distance_error else np.nan)

    set_speed = config['acc_settings']['set_speed']
    speeds = np.array(speeds)

    # Rise time
    target_90 = 0.9 * set_speed
    rise_time_idx = np.argmax(speeds >= target_90)
    rise_time = sensor_df['time'].iloc[rise_time_idx] if speeds[rise_time_idx] >= target_90 else 150.0

    # Overshoot
    max_speed = speeds.max()
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Speed steady-state error (last 50s)
    steady_idx = int(500)
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


def evaluate_gains(gains: dict, config: dict, sensor_df: pd.DataFrame, dt: float) -> tuple:
    config['pid_speed'] = {'kp': gains['kp_speed'], 'ki': gains['ki_speed'], 'kd': gains['kd_speed']}
    config['pid_distance'] = {'kp': gains['kp_distance'], 'ki': gains['ki_distance'], 'kd': gains['kd_distance']}

    metrics = run_simulation_eval(config, sensor_df, dt)

    cost = 0.0
    penalty_details = {}

    # Rise time penalty (< 10s) - weight 100
    if metrics['rise_time'] > 10:
        cost += (metrics['rise_time'] - 10) * 100
        penalty_details['rise_time'] = (metrics['rise_time'] - 10) * 100
    else:
        penalty_details['rise_time'] = 0

    # Overshoot penalty (< 5%) - weight 200
    if metrics['overshoot'] > 5:
        cost += (metrics['overshoot'] - 5) * 200
        penalty_details['overshoot'] = (metrics['overshoot'] - 5) * 200
    else:
        penalty_details['overshoot'] = 0

    # Speed steady-state error penalty (< 0.5 m/s) - weight 300
    if metrics['speed_steady_error'] > 0.5:
        cost += (metrics['speed_steady_error'] - 0.5) * 300
        penalty_details['speed_steady'] = (metrics['speed_steady_error'] - 0.5) * 300
    else:
        penalty_details['speed_steady'] = 0

    # Min distance penalty (> 5m) - weight 500
    if metrics['min_distance'] < 5:
        cost += (5 - metrics['min_distance']) * 500
        penalty_details['min_dist'] = (5 - metrics['min_distance']) * 500
    else:
        penalty_details['min_dist'] = 0

    # Distance steady-state error penalty (< 2m) - weight 100
    if metrics['distance_steady_error'] > 2:
        cost += (metrics['distance_steady_error'] - 2) * 100
        penalty_details['dist_steady'] = (metrics['distance_steady_error'] - 2) * 100
    else:
        penalty_details['dist_steady'] = 0

    return cost, metrics, penalty_details


def final_tuning(config_path: str, sensor_data_path: str, output_path: str, n_iterations: int = 3000):
    config = load_config(config_path)
    sensor_df = pd.read_csv(sensor_data_path)
    dt = config.get('simulation', {}).get('dt', 0.1)

    best_cost = float('inf')
    best_gains = None
    best_metrics = None
    best_penalties = None

    print(f"Starting final tuning with {n_iterations} iterations...")

    np.random.seed(42)
    for i in range(n_iterations):
        # Search space
        gains = {
            'kp_speed': np.random.uniform(0.3, 1.5),
            'ki_speed': np.random.uniform(0.05, 0.3),
            'kd_speed': np.random.uniform(0.2, 1.5),
            'kp_distance': np.random.uniform(0.05, 0.3),
            'ki_distance': np.random.uniform(0.01, 0.1),
            'kd_distance': np.random.uniform(0.1, 0.8)
        }

        cost, metrics, penalties = evaluate_gains(gains, config.copy(), sensor_df, dt)

        if cost < best_cost:
            best_cost = cost
            best_gains = gains
            best_metrics = metrics
            best_penalties = penalties

        if (i + 1) % 500 == 0:
            print(f"Iteration {i+1}/{n_iterations}, current best cost: {best_cost:.2f}")

    print(f"\n{'='*50}")
    print("BEST GAINS FOUND:")
    print(f"Speed PID: kp={best_gains['kp_speed']:.4f}, ki={best_gains['ki_speed']:.4f}, kd={best_gains['kd_speed']:.4f}")
    print(f"Distance PID: kp={best_gains['kp_distance']:.4f}, ki={best_gains['ki_distance']:.4f}, kd={best_gains['kd_distance']:.4f}")
    print(f"\nPERFORMANCE METRICS:")
    print(f"Rise time: {best_metrics['rise_time']:.2f}s (target: <10s) - penalty: {best_penalties['rise_time']:.2f}")
    print(f"Overshoot: {best_metrics['overshoot']:.2f}% (target: <5%) - penalty: {best_penalties['overshoot']:.2f}")
    print(f"Speed steady-state error: {best_metrics['speed_steady_error']:.4f} m/s (target: <0.5) - penalty: {best_penalties['speed_steady']:.2f}")
    print(f"Min distance: {best_metrics['min_distance']:.2f}m (target: >5m) - penalty: {best_penalties['min_dist']:.2f}")
    print(f"Distance steady-state error: {best_metrics['distance_steady_error']:.2f}m (target: <2m) - penalty: {best_penalties['dist_steady']:.2f}")
    print(f"\nTOTAL COST: {best_cost:.2f}")

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
    final_tuning(
        config_path='vehicle_params.yaml',
        sensor_data_path='sensor_data.csv',
        output_path='tuning_results.yaml',
        n_iterations=3000
    )

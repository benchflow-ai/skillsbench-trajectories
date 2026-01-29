"""PID parameter tuning script using grid search."""

import csv
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def evaluate_tuning(pid_params, config, sensor_data, dt):
    """
    Evaluate PID tuning with given parameters.

    Returns metrics dict with rise time, overshoot, steady-state error, etc.
    """
    # Update config with new PID parameters
    config_copy = yaml.safe_load(yaml.dump(config))
    config_copy['pid_speed']['kp'] = pid_params[0]
    config_copy['pid_speed']['ki'] = pid_params[1]
    config_copy['pid_speed']['kd'] = pid_params[2]
    config_copy['pid_distance']['kp'] = pid_params[3]
    config_copy['pid_distance']['ki'] = pid_params[4]
    config_copy['pid_distance']['kd'] = pid_params[5]

    acc = AdaptiveCruiseControl(config_copy)
    set_speed = config['acc_settings']['set_speed']

    ego_speed = 0.0
    speeds = []
    distance_errors = []
    distances = []
    modes = []
    first_reach_90 = None
    max_speed = 0.0

    for sensor in sensor_data:
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        accel_cmd = max(config['vehicle']['max_deceleration'],
                       min(config['vehicle']['max_acceleration'], accel_cmd))

        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        speeds.append(ego_speed)
        if dist_error is not None:
            distance_errors.append(dist_error)
        if distance is not None:
            distances.append(distance)
        modes.append(mode)

        max_speed = max(max_speed, ego_speed)
        if first_reach_90 is None and ego_speed >= 0.9 * set_speed:
            first_reach_90 = len(speeds)

    # Calculate metrics
    metrics = {}

    # Speed rise time (to 90% of set speed)
    if first_reach_90 is not None:
        metrics['rise_time'] = first_reach_90 * dt
    else:
        metrics['rise_time'] = 150.0

    # Speed overshoot
    if max_speed > set_speed:
        metrics['overshoot'] = ((max_speed - set_speed) / set_speed) * 100
    else:
        metrics['overshoot'] = 0.0

    # Speed steady-state error (last 30 seconds)
    steady_state_idx = max(0, len(speeds) - int(30 / dt))
    steady_speeds = speeds[steady_state_idx:]
    if steady_speeds:
        metrics['speed_sse'] = abs(np.mean(steady_speeds) - set_speed)
    else:
        metrics['speed_sse'] = abs(speeds[-1] - set_speed)

    # Distance steady-state error (last 30 seconds in follow mode)
    follow_distance_errors = [distance_errors[i] for i in range(len(distance_errors))
                             if i + steady_state_idx < len(modes)
                             and modes[i + steady_state_idx] == 'follow']
    if follow_distance_errors:
        metrics['distance_sse'] = abs(np.mean(follow_distance_errors))
    else:
        metrics['distance_sse'] = 0.0

    # Minimum distance constraint
    follow_distances = [distances[i] for i in range(len(distances))
                       if i + steady_state_idx < len(modes)
                       and modes[i + steady_state_idx] == 'follow']
    if follow_distances:
        metrics['min_distance_achieved'] = min(follow_distances)
    else:
        metrics['min_distance_achieved'] = float('inf')

    return metrics


def objective_function(pid_params, config, sensor_data, dt):
    """
    Objective function to minimize.

    Weighted combination of performance metrics.
    """
    try:
        metrics = evaluate_tuning(pid_params, config, sensor_data, dt)

        cost = 0.0

        # Rise time cost (target < 10s)
        rise_time_cost = max(0, metrics['rise_time'] - 10.0)

        # Overshoot cost (target < 5%)
        overshoot_cost = max(0, metrics['overshoot'] - 5.0) * 2.0

        # Speed SSE cost (target < 0.5 m/s)
        speed_sse_cost = max(0, metrics['speed_sse'] - 0.5) * 5.0

        # Distance SSE cost (target < 2m)
        distance_sse_cost = max(0, metrics['distance_sse'] - 2.0) * 3.0

        # Minimum distance cost (target > 5m)
        min_dist_cost = max(0, 5.0 - metrics['min_distance_achieved']) * 10.0

        cost = (rise_time_cost + overshoot_cost + speed_sse_cost +
                distance_sse_cost + min_dist_cost)

        return cost

    except Exception as e:
        return 1e6


def tune_pid(config, sensor_data):
    """
    Tune PID parameters using grid search.

    Returns tuned parameters array.
    """
    dt = config['simulation']['dt']

    # Grid search with reasonable step sizes
    kp_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ki_values = [0.01, 0.05, 0.1, 0.2, 0.3]
    kd_values = [0.0, 0.1, 0.5, 1.0]

    print("Starting PID parameter grid search optimization...")

    best_cost = float('inf')
    best_params = None

    for kp_speed in kp_values:
        for ki_speed in ki_values:
            for kd_speed in kd_values:
                for kp_dist in [0.5, 1.0, 1.5, 2.0]:
                    for ki_dist in [0.01, 0.05, 0.1, 0.2]:
                        for kd_dist in [0.0, 0.1, 0.5]:
                            params = np.array([kp_speed, ki_speed, kd_speed,
                                              kp_dist, ki_dist, kd_dist])
                            cost = objective_function(params, config, sensor_data, dt)

                            if cost < best_cost:
                                best_cost = cost
                                best_params = params
                                print(f"New best cost: {best_cost:.4f} | "
                                      f"kp_s={kp_speed:.2f}, ki_s={ki_speed:.3f}, "
                                      f"kd_s={kd_speed:.2f}, kp_d={kp_dist:.2f}, "
                                      f"ki_d={ki_dist:.3f}, kd_d={kd_dist:.2f}")

    print(f"\nOptimization complete (best objective: {best_cost:.4f})")
    print(f"Best parameters found:")
    print(f"  pid_speed: kp={best_params[0]:.4f}, ki={best_params[1]:.4f}, "
          f"kd={best_params[2]:.4f}")
    print(f"  pid_distance: kp={best_params[3]:.4f}, ki={best_params[4]:.4f}, "
          f"kd={best_params[5]:.4f}")

    # Evaluate final metrics
    final_metrics = evaluate_tuning(best_params, config, sensor_data, dt)
    print(f"\nFinal Metrics:")
    print(f"  Rise time: {final_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {final_metrics['overshoot']:.2f}% (target: <5%)")
    print(f"  Speed SSE: {final_metrics['speed_sse']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance SSE: {final_metrics['distance_sse']:.3f}m (target: <2m)")
    print(f"  Min distance: {final_metrics['min_distance_achieved']:.2f}m "
          f"(target: >5m)")

    return best_params


def save_tuning_results(pid_params, output_file):
    """Save tuned parameters to YAML file."""
    tuning_data = {
        'pid_speed': {
            'kp': float(pid_params[0]),
            'ki': float(pid_params[1]),
            'kd': float(pid_params[2])
        },
        'pid_distance': {
            'kp': float(pid_params[3]),
            'ki': float(pid_params[4]),
            'kd': float(pid_params[5])
        }
    }

    with open(output_file, 'w') as f:
        yaml.dump(tuning_data, f, default_flow_style=False)

    print(f"\nTuning results saved to {output_file}")


def main():
    """Main tuning runner."""
    config = load_config('vehicle_params.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')

    tuned_params = tune_pid(config, sensor_data)
    save_tuning_results(tuned_params, 'tuning_results.yaml')


if __name__ == '__main__':
    main()

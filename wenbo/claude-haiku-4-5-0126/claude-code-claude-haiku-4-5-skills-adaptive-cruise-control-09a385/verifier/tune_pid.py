"""
PID tuning script for ACC system.

Uses Ziegler-Nichols-inspired tuning and optimization to find good PID gains.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl
from simulation import update_vehicle_state, calculate_ttc


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_file):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_file, 'r') as f:
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


def run_sim_with_params(config, sensor_data, pid_speed_params, pid_distance_params):
    """
    Run simulation with specific PID parameters.

    Returns:
        dict: Metrics including rise_time, overshoot, steady_state_error, etc.
    """
    config['pid_speed'] = pid_speed_params
    config['pid_distance'] = pid_distance_params

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    # Cruise phase metrics
    cruise_speeds = []
    cruise_times = []
    cruise_start_time = None
    target_speed_reached = False
    rise_time = None

    # Follow phase metrics
    follow_distance_errors = []
    follow_distances = []
    follow_start_time = None

    for sensor_point in sensor_data:
        time = sensor_point['time']
        lead_speed = sensor_point['lead_speed']
        distance = sensor_point['distance']

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update vehicle state
        ego_speed = update_vehicle_state(
            ego_speed,
            accel_cmd,
            dt,
            config['vehicle']['max_acceleration'],
            config['vehicle']['max_deceleration']
        )

        # Cruise phase metrics (no lead vehicle)
        if lead_speed is None:
            if cruise_start_time is None:
                cruise_start_time = time
            cruise_speeds.append(ego_speed)
            cruise_times.append(time)

            # Check for 90% rise time (5% settling)
            if not target_speed_reached and ego_speed >= set_speed * 0.9:
                rise_time = time - cruise_start_time
                target_speed_reached = True

        # Follow phase metrics (lead vehicle present)
        else:
            if follow_start_time is None:
                follow_start_time = time
            if distance_error is not None:
                follow_distance_errors.append(distance_error)
            if distance is not None:
                follow_distances.append(distance)

    # Calculate metrics
    metrics = {}

    # Speed control metrics (cruise phase)
    if cruise_speeds:
        metrics['rise_time'] = rise_time if rise_time is not None else float('inf')
        final_cruise_speed = cruise_speeds[-1]
        metrics['cruise_steady_state_speed'] = final_cruise_speed
        metrics['speed_steady_state_error'] = abs(set_speed - final_cruise_speed)

        # Overshoot calculation
        if target_speed_reached:
            max_speed = max(cruise_speeds)
            if max_speed > set_speed:
                metrics['speed_overshoot_percent'] = 100 * (max_speed - set_speed) / set_speed
            else:
                metrics['speed_overshoot_percent'] = 0
        else:
            metrics['speed_overshoot_percent'] = 0

    # Distance control metrics (follow phase)
    if follow_distance_errors:
        final_distance_error = follow_distance_errors[-1]
        metrics['distance_steady_state_error'] = abs(final_distance_error)
        metrics['follow_distance_errors'] = follow_distance_errors
    else:
        metrics['distance_steady_state_error'] = float('inf')

    if follow_distances:
        min_distance = min(follow_distances)
        metrics['minimum_distance'] = min_distance
    else:
        metrics['minimum_distance'] = float('inf')

    return metrics


def evaluate_params(config, sensor_data, pid_speed_params, pid_distance_params):
    """
    Evaluate a parameter set against performance targets.

    Returns:
        float: Score (lower is better)
    """
    metrics = run_sim_with_params(config, sensor_data, pid_speed_params, pid_distance_params)

    # Define target values and weights
    targets = {
        'rise_time': (10.0, 1.0),  # (target, weight)
        'speed_overshoot_percent': (5.0, 1.0),
        'speed_steady_state_error': (0.5, 1.0),
        'distance_steady_state_error': (2.0, 1.5),
        'minimum_distance': (5.0, 1.5),
    }

    score = 0.0
    for key, (target, weight) in targets.items():
        actual = metrics.get(key, float('inf'))

        # Calculate normalized error
        if actual == float('inf'):
            error = 100.0
        elif key == 'minimum_distance':
            # For minimum distance, we want it > target, so penalize if lower
            if actual < target:
                error = 100 * (target - actual) / target
            else:
                error = 0
        else:
            # For others, minimize difference from target
            error = abs(actual - target) / max(target, 1.0)

        score += error * weight

    return score, metrics


def tune_pid_params(config_file, sensor_file):
    """
    Tune PID parameters to meet performance targets.

    Returns:
        dict: Best parameter set and metrics
    """
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    # Grid search for initial parameter tuning
    best_score = float('inf')
    best_params = None
    best_metrics = None

    # Parameter ranges
    kp_range = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ki_range = [0.05, 0.1, 0.15, 0.2, 0.25]
    kd_range = [0.1, 0.2, 0.3, 0.5, 0.8]

    print("Tuning PID parameters...")
    total_iterations = len(kp_range) * len(ki_range) * len(kd_range) * len(kp_range) * len(ki_range) * len(kd_range)
    iteration = 0

    for speed_kp in kp_range:
        for speed_ki in ki_range:
            for speed_kd in kd_range:
                for dist_kp in kp_range:
                    for dist_ki in ki_range:
                        for dist_kd in kd_range:
                            iteration += 1
                            if iteration % 100 == 0:
                                print(f"  Iteration {iteration}/{total_iterations}, Best score: {best_score:.4f}")

                            speed_params = {
                                'kp': speed_kp,
                                'ki': speed_ki,
                                'kd': speed_kd
                            }

                            dist_params = {
                                'kp': dist_kp,
                                'ki': dist_ki,
                                'kd': dist_kd
                            }

                            score, metrics = evaluate_params(
                                config, sensor_data,
                                speed_params, dist_params
                            )

                            if score < best_score:
                                best_score = score
                                best_params = {
                                    'pid_speed': speed_params,
                                    'pid_distance': dist_params
                                }
                                best_metrics = metrics

    print(f"\nTuning complete!")
    print(f"Best score: {best_score:.4f}")
    print(f"\nBest parameters:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']}, ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']}, ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print(f"\nPerformance metrics:")
    for key, value in best_metrics.items():
        if key not in ['follow_distance_errors']:
            print(f"  {key}: {value:.4f}")

    return best_params, best_metrics


def save_tuning_results(params, output_file):
    """Save tuning results to YAML file."""
    data = {
        'pid_speed': params['pid_speed'],
        'pid_distance': params['pid_distance']
    }

    with open(output_file, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)

    print(f"\nTuning results saved to {output_file}")


if __name__ == '__main__':
    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else '/root/vehicle_params.yaml'
    sensor_file = sys.argv[2] if len(sys.argv) > 2 else '/root/sensor_data.csv'
    output_file = sys.argv[3] if len(sys.argv) > 3 else '/root/tuning_results.yaml'

    params, metrics = tune_pid_params(config_file, sensor_file)
    save_tuning_results(params, output_file)

"""
Improved PID tuning script using focused search and multi-phase optimization.
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
    """Run simulation with specific PID parameters and return metrics."""
    config['pid_speed'] = pid_speed_params
    config['pid_distance'] = pid_distance_params

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    cruise_speeds = []
    cruise_times = []
    cruise_start_time = None
    target_speed_reached = False
    rise_time = None

    follow_distance_errors = []
    follow_distances = []
    follow_min_distance = float('inf')
    follow_start_idx = None

    for idx, sensor_point in enumerate(sensor_data):
        time = sensor_point['time']
        lead_speed = sensor_point['lead_speed']
        distance = sensor_point['distance']

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        ego_speed = update_vehicle_state(
            ego_speed,
            accel_cmd,
            dt,
            config['vehicle']['max_acceleration'],
            config['vehicle']['max_deceleration']
        )

        if lead_speed is None:
            if cruise_start_time is None:
                cruise_start_time = time
            cruise_speeds.append(ego_speed)
            cruise_times.append(time)

            if not target_speed_reached and ego_speed >= set_speed * 0.9:
                rise_time = time - cruise_start_time
                target_speed_reached = True

        else:
            if follow_start_idx is None:
                follow_start_idx = idx
            if distance_error is not None:
                follow_distance_errors.append(distance_error)
            if distance is not None:
                follow_distances.append(distance)
                if distance < follow_min_distance:
                    follow_min_distance = distance

    metrics = {}

    if cruise_speeds:
        metrics['rise_time'] = rise_time if rise_time is not None else float('inf')
        final_cruise_speed = cruise_speeds[-1]
        metrics['cruise_steady_state_speed'] = final_cruise_speed
        metrics['speed_steady_state_error'] = abs(set_speed - final_cruise_speed)

        if target_speed_reached:
            max_speed = max(cruise_speeds)
            if max_speed > set_speed:
                metrics['speed_overshoot_percent'] = 100 * (max_speed - set_speed) / set_speed
            else:
                metrics['speed_overshoot_percent'] = 0
        else:
            metrics['speed_overshoot_percent'] = 0

    # Focus on last 20% of follow phase for steady state
    if follow_distance_errors:
        steadystate_start = max(0, len(follow_distance_errors) - len(follow_distance_errors) // 5)
        steadystate_errors = follow_distance_errors[steadystate_start:]
        if steadystate_errors:
            final_distance_error = steadystate_errors[-1]
            metrics['distance_steady_state_error'] = abs(final_distance_error)
        else:
            metrics['distance_steady_state_error'] = abs(follow_distance_errors[-1])
    else:
        metrics['distance_steady_state_error'] = float('inf')

    metrics['minimum_distance'] = follow_min_distance if follow_min_distance != float('inf') else float('inf')

    return metrics


def evaluate_params(config, sensor_data, pid_speed_params, pid_distance_params):
    """Evaluate parameter set against targets."""
    metrics = run_sim_with_params(config, sensor_data, pid_speed_params, pid_distance_params)

    # Separate scoring for cruise and follow phases
    cruise_score = 0.0
    follow_score = 0.0

    # Cruise phase metrics
    rise_time = metrics.get('rise_time', float('inf'))
    if rise_time < 10.0:
        cruise_score += (10.0 - rise_time)
    else:
        cruise_score += (rise_time - 10.0) * 2

    overshoot = metrics.get('speed_overshoot_percent', 0)
    if overshoot < 5.0:
        cruise_score += overshoot * 0.1
    else:
        cruise_score += (overshoot - 5.0) * 0.5

    speed_error = metrics.get('speed_steady_state_error', 0)
    cruise_score += speed_error * 10.0

    # Follow phase metrics (higher weight)
    distance_error = metrics.get('distance_steady_state_error', float('inf'))
    if distance_error < 2.0:
        follow_score += (2.0 - distance_error) * 5
    else:
        follow_score += min(distance_error - 2.0, 50.0) * 5

    min_dist = metrics.get('minimum_distance', float('inf'))
    if min_dist >= 5.0:
        follow_score += 0
    else:
        follow_score += (5.0 - min_dist) * 20

    total_score = cruise_score + follow_score

    return total_score, metrics


def tune_pid_focused(config_file, sensor_file):
    """Focused tuning with emphasis on distance control."""
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    best_score = float('inf')
    best_params = None
    best_metrics = None

    # Focus on parameters with larger ranges for distance control
    speed_kp_range = [0.5, 1.0, 1.5, 2.0]
    speed_ki_range = [0.05, 0.1, 0.15, 0.2]
    speed_kd_range = [0.1, 0.2, 0.3]

    dist_kp_range = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    dist_ki_range = [0.3, 0.4, 0.5, 0.6, 0.7]
    dist_kd_range = [0.5, 1.0, 1.5, 2.0]

    print("Performing focused PID tuning...")
    total_iterations = (len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) *
                       len(dist_kp_range) * len(dist_ki_range) * len(dist_kd_range))
    iteration = 0

    for speed_kp in speed_kp_range:
        for speed_ki in speed_ki_range:
            for speed_kd in speed_kd_range:
                for dist_kp in dist_kp_range:
                    for dist_ki in dist_ki_range:
                        for dist_kd in dist_kd_range:
                            iteration += 1
                            if iteration % 200 == 0:
                                print(f"  Iteration {iteration}/{total_iterations}, Best score: {best_score:.2f}")

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

    print(f"\nFocused tuning complete!")
    print(f"Best score: {best_score:.2f}")
    print(f"\nBest parameters:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']}, ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']}, ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print(f"\nPerformance metrics:")
    for key, value in best_metrics.items():
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

    params, metrics = tune_pid_focused(config_file, sensor_file)
    save_tuning_results(params, output_file)

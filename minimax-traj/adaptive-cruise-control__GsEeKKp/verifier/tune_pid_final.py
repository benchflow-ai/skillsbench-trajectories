"""Fast PID Parameter Tuning for ACC System (Final Version)."""

import yaml
import csv
from acc_system import AdaptiveCruiseControl


def load_sensor_data(csv_path='sensor_data.csv'):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed']) if row['ego_speed'] else 0.0
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else 0.0
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def evaluate_parameters(kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist):
    """Evaluate PID parameters and return performance metrics."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Update PID parameters
    config['pid_speed'] = {'kp': kp_speed, 'ki': ki_speed, 'kd': kd_speed}
    # Distance controller kp should be negative for our error sign convention
    config['pid_distance'] = {'kp': -abs(kp_dist), 'ki': -abs(ki_dist), 'kd': -abs(kd_dist)}

    # Load sensor data
    sensor_data = load_sensor_data()

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']
    max_acceleration = config['vehicle']['max_acceleration']
    max_deceleration = config['vehicle']['max_deceleration']

    # Initialize simulation state
    current_speed = 0.0
    max_speed = 0.0
    min_distance = float('inf')
    speed_rise_time = None
    target_speed = 0.9 * set_speed

    # Track steady-state errors
    speed_errors_cruise = []
    distance_errors_follow = []
    distances = []

    # Run simulation
    for i, data_point in enumerate(sensor_data):
        lead_speed = data_point['lead_speed']
        distance = data_point['distance']

        # Compute ACC control command
        acceleration_cmd, mode, distance_error = acc.compute(
            current_speed, lead_speed, distance, dt
        )

        # Apply acceleration limits
        acceleration_cmd = max(min(acceleration_cmd, max_acceleration), max_deceleration)

        # Update vehicle speed
        current_speed += acceleration_cmd * dt
        current_speed = max(0.0, current_speed)
        max_speed = max(max_speed, current_speed)

        # Track metrics
        if speed_rise_time is None and current_speed >= target_speed:
            speed_rise_time = data_point['time']

        if distance > 0:
            min_distance = min(min_distance, distance)
            distances.append(distance)

        # Track steady-state errors (last 50 seconds)
        if data_point['time'] > 100:
            if mode == 'cruise':
                speed_errors_cruise.append(abs(set_speed - current_speed))
            elif mode == 'follow':
                if distance_error is not None:
                    distance_errors_follow.append(abs(distance_error))

    # Calculate metrics
    speed_overshoot = max(0, (max_speed - set_speed) / set_speed * 100)
    speed_steady_state_error = sum(speed_errors_cruise) / len(speed_errors_cruise) if speed_errors_cruise else 999
    distance_steady_state_error = sum(distance_errors_follow) / len(distance_errors_follow) if distance_errors_follow else 999

    # Calculate score (lower is better)
    score = 0.0
    if speed_rise_time and speed_rise_time > 10:
        score += (speed_rise_time - 10) * 10
    if speed_overshoot > 5:
        score += (speed_overshoot - 5) * 100
    if speed_steady_state_error > 0.5:
        score += (speed_steady_state_error - 0.5) * 100
    if distance_steady_state_error > 2:
        score += (distance_steady_state_error - 2) * 50
    if min_distance <= 5:
        score += (5 - min_distance) * 1000

    return score, speed_rise_time if speed_rise_time else 999, speed_overshoot, min_distance, speed_steady_state_error, distance_steady_state_error


def tune_parameters():
    """Tune PID parameters using grid search."""
    print("Starting PID parameter tuning...")

    best_score = float('inf')
    best_params = None
    best_metrics = None

    # Limited grid search with kp in (0, 10), ki in [0, 5), kd in [0, 5)
    kp_speed_values = [0.5, 0.8, 1.0, 1.2, 1.5]
    ki_speed_values = [0.0, 0.05, 0.1]
    kd_speed_values = [0.0, 0.1, 0.2]

    kp_dist_values = [0.3, 0.5, 0.8, 1.0]
    ki_dist_values = [0.0, 0.05, 0.1]
    kd_dist_values = [0.0, 0.1, 0.2]

    total_combinations = (len(kp_speed_values) * len(ki_speed_values) * len(kd_speed_values) *
                         len(kp_dist_values) * len(ki_dist_values) * len(kd_dist_values))
    current_combination = 0

    print(f"Testing {total_combinations} parameter combinations...")

    # Grid search
    for kp_s in kp_speed_values:
        for ki_s in ki_speed_values:
            for kd_s in kd_speed_values:
                for kp_d in kp_dist_values:
                    for ki_d in ki_dist_values:
                        for kd_d in kd_dist_values:
                            current_combination += 1
                            print(f"\rProgress: {current_combination}/{total_combinations} ({100*current_combination/total_combinations:.1f}%)", end='', flush=True)

                            score, rise_time, overshoot, min_dist, ss_speed_err, ss_dist_err = evaluate_parameters(
                                kp_s, ki_s, kd_s, kp_d, ki_d, kd_d
                            )

                            if score < best_score:
                                best_score = score
                                best_params = {
                                    'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                    'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
                                }
                                best_metrics = {
                                    'speed_rise_time': rise_time,
                                    'speed_overshoot': overshoot,
                                    'min_distance': min_dist,
                                    'speed_steady_state_error': ss_speed_err,
                                    'distance_steady_state_error': ss_dist_err
                                }

    print("\n\nTuning complete!")
    print(f"\nBest score: {best_score:.2f}")
    print(f"Best parameters:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']:.2f}, ki={best_params['pid_speed']['ki']:.2f}, kd={best_params['pid_speed']['kd']:.2f}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']:.2f}, ki={best_params['pid_distance']['ki']:.2f}, kd={best_params['pid_distance']['kd']:.2f}")
    print(f"\nPerformance metrics:")
    print(f"  Speed rise time: {best_metrics['speed_rise_time']:.2f}s")
    print(f"  Speed overshoot: {best_metrics['speed_overshoot']:.2f}%")
    print(f"  Speed steady-state error: {best_metrics['speed_steady_state_error']:.2f} m/s")
    print(f"  Distance steady-state error: {best_metrics['distance_steady_state_error']:.2f} m")
    print(f"  Minimum distance: {best_metrics['min_distance']:.2f} m")

    # Save tuning results
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_params, f, default_flow_style=False)

    print(f"\nTuning results saved to tuning_results.yaml")

    return best_params, best_metrics


if __name__ == '__main__':
    tune_parameters()

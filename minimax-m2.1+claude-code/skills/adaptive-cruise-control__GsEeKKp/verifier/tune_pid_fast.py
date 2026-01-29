"""Fast PID Parameter Tuning for ACC System."""

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
    config['pid_distance'] = {'kp': kp_dist, 'ki': ki_dist, 'kd': kd_dist}

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

    # Calculate metrics
    speed_overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Check if targets are met
    score = 0.0
    if speed_rise_time and speed_rise_time > 10:
        score += (speed_rise_time - 10) * 10
    if speed_overshoot > 5:
        score += (speed_overshoot - 5) * 100
    if min_distance <= 5:
        score += (5 - min_distance) * 1000

    return score, speed_rise_time if speed_rise_time else 999, speed_overshoot, min_distance


def tune_parameters():
    """Tune PID parameters using grid search with limited combinations."""
    print("Starting PID parameter tuning...")

    best_score = float('inf')
    best_params = None

    # Limited grid search
    kp_speed_values = [1.0, 2.0, 3.0]
    ki_speed_values = [0.0, 0.1]
    kd_speed_values = [0.0, 0.1]

    kp_dist_values = [0.5, 1.0, 2.0]
    ki_dist_values = [0.0, 0.1]
    kd_dist_values = [0.0, 0.1]

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

                            score, rise_time, overshoot, min_dist = evaluate_parameters(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)

                            if score < best_score:
                                best_score = score
                                best_params = {
                                    'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                    'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
                                }

    print("\n\nTuning complete!")
    print(f"\nBest score: {best_score:.2f}")
    print(f"Best parameters:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']:.2f}, ki={best_params['pid_speed']['ki']:.2f}, kd={best_params['pid_speed']['kd']:.2f}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']:.2f}, ki={best_params['pid_distance']['ki']:.2f}, kd={best_params['pid_distance']['kd']:.2f}")

    # Save tuning results
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_params, f, default_flow_style=False)

    print(f"\nTuning results saved to tuning_results.yaml")

    return best_params


if __name__ == '__main__':
    tune_parameters()

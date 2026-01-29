"""PID Parameter Tuning for ACC System."""

import yaml
import csv
import copy
from acc_system import AdaptiveCruiseControl
from pid_controller import PIDController


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
    speed_errors = []
    min_distances = []

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

        # Track metrics
        if mode == 'cruise':
            speed_error = abs(set_speed - current_speed)
            speed_errors.append(speed_error)

        if distance > 0:
            min_distances.append(distance)

    # Calculate performance metrics
    speed_rise_time = None
    speed_overshoot = 0.0
    speed_steady_state_error = 0.0
    distance_steady_state_error = 0.0
    min_distance = min(min_distances) if min_distances else float('inf')

    # Calculate rise time (time to reach 90% of set speed)
    target_speed = 0.9 * set_speed
    for i, data_point in enumerate(sensor_data):
        if i < len(speed_errors):
            continue
        # Simpler approach: check when speed first reaches 90% of set speed
        pass

    # Calculate steady-state error (average error in last 50 seconds)
    last_50_seconds = int(50 / dt)
    if len(speed_errors) > last_50_seconds:
        speed_steady_state_error = sum(speed_errors[-last_50_seconds:]) / last_50_seconds

    # Calculate distance steady-state error (average error in last 50 seconds when in follow mode)
    distance_errors = []
    current_speed = 0.0
    acc = AdaptiveCruiseControl(config)

    for i, data_point in enumerate(sensor_data):
        lead_speed = data_point['lead_speed']
        distance = data_point['distance']

        if lead_speed is not None and lead_speed > 0:
            desired_distance = config['acc_settings']['min_distance'] + current_speed * config['acc_settings']['time_headway']
            distance_error = abs(desired_distance - distance)
            distance_errors.append(distance_error)

        acceleration_cmd, mode, _ = acc.compute(current_speed, lead_speed, distance, dt)
        acceleration_cmd = max(min(acceleration_cmd, max_acceleration), max_deceleration)
        current_speed += acceleration_cmd * dt
        current_speed = max(0.0, current_speed)

    if len(distance_errors) > last_50_seconds:
        distance_steady_state_error = sum(distance_errors[-last_50_seconds:]) / last_50_seconds

    # Calculate overshoot (max speed - set_speed) / set_speed
    speed_max = max([d['ego_speed'] for d in sensor_data])
    speed_overshoot = max(0, (speed_max - set_speed) / set_speed * 100)

    # Calculate rise time more accurately
    for i, data_point in enumerate(sensor_data):
        if data_point['ego_speed'] >= target_speed:
            speed_rise_time = data_point['time']
            break

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

    return {
        'score': score,
        'speed_rise_time': speed_rise_time if speed_rise_time else 999,
        'speed_overshoot': speed_overshoot,
        'speed_steady_state_error': speed_steady_state_error,
        'distance_steady_state_error': distance_steady_state_error,
        'min_distance': min_distance
    }


def tune_parameters():
    """Tune PID parameters using grid search."""
    print("Starting PID parameter tuning...")

    best_score = float('inf')
    best_params = None
    best_metrics = None

    # Grid search parameters
    kp_speed_values = [0.5, 1.0, 1.5, 2.0, 2.5]
    ki_speed_values = [0.0, 0.1, 0.2, 0.3]
    kd_speed_values = [0.0, 0.1, 0.2]

    kp_dist_values = [0.5, 1.0, 1.5, 2.0, 2.5]
    ki_dist_values = [0.0, 0.1, 0.2, 0.3]
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

                            metrics = evaluate_parameters(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)

                            if metrics['score'] < best_score:
                                best_score = metrics['score']
                                best_params = {
                                    'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                    'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
                                }
                                best_metrics = metrics

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

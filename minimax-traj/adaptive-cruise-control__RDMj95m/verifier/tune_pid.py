"""PID Parameter Tuning for Adaptive Cruise Control System"""

import csv
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_config(yaml_file):
    """Load configuration from YAML file."""
    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_file):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def evaluate_performance(results, config):
    """
    Evaluate ACC performance against requirements.

    Args:
        results (list): Simulation results
        config (dict): ACC configuration

    Returns:
        dict: Performance metrics and score
    """
    set_speed = config['acc_settings']['set_speed']
    dt = config['simulation']['dt']

    # Extract time series
    times = [r['time'] for r in results]
    speeds = [r['ego_speed'] for r in results]
    accelerations = [r['acceleration_cmd'] for r in results]
    modes = [r['mode'] for r in results]

    # 1. Speed rise time (time to reach 90% of set speed)
    target_speed = 0.9 * set_speed
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= target_speed:
            rise_time = times[i]
            break

    # 2. Speed overshoot (max overshoot above set speed)
    max_speed = max(speeds)
    overshoot_percent = max(0, (max_speed - set_speed) / set_speed * 100)

    # 3. Speed steady-state error (error in last 10 seconds)
    steady_state_start_idx = int(len(times) * 0.9)
    steady_state_errors = [abs(s - set_speed) for s in speeds[steady_state_start_idx:]]
    steady_state_error = np.mean(steady_state_errors) if steady_state_errors else 0

    # 4. Distance steady-state error (for follow mode in last 10 seconds)
    distance_errors_follow = []
    for i in range(steady_state_start_idx, len(results)):
        if results[i]['mode'] == 'follow' and results[i]['distance'] != '':
            distance_errors_follow.append(abs(results[i]['distance_error']))

    distance_ss_error = np.mean(distance_errors_follow) if distance_errors_follow else 0

    # 5. Minimum distance check
    min_distance = float('inf')
    emergency_activations = 0
    for r in results:
        if r['distance'] != '':
            dist = float(r['distance'])
            min_distance = min(min_distance, dist)
            if r['mode'] == 'emergency':
                emergency_activations += 1

    # Calculate score (lower is better)
    # Penalize violations of requirements
    score = 0

    if rise_time is None or rise_time > 10:
        score += 1000  # Severe penalty for not meeting rise time
    else:
        score += rise_time  # Add rise time to score

    if overshoot_percent > 5:
        score += (overshoot_percent - 5) * 10  # Penalty for overshoot

    if steady_state_error > 0.5:
        score += (steady_state_error - 0.5) * 100  # High penalty for steady-state error

    if distance_ss_error > 2:
        score += (distance_ss_error - 2) * 50  # Penalty for distance error

    if min_distance <= 5:
        score += 1000  # Severe penalty for too small distance

    # Bonus for smooth operation
    acc_variance = np.var(accelerations)
    score += acc_variance  # Prefer smooth acceleration

    return {
        'rise_time': rise_time,
        'overshoot_percent': overshoot_percent,
        'steady_state_error': steady_state_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance,
        'emergency_activations': emergency_activations,
        'score': score
    }


def run_simulation(config, sensor_data, pid_gains):
    """
    Run ACC simulation with given PID gains.

    Args:
        config (dict): Vehicle and ACC configuration
        sensor_data (list): Sensor data
        pid_gains (dict): PID gains for speed and distance

    Returns:
        list: Simulation results
    """
    # Update config with gains
    config['pid_speed'] = pid_gains['pid_speed']
    config['pid_distance'] = pid_gains['pid_distance']

    # Initialize ACC
    acc = AdaptiveCruiseControl(config)

    # Run simulation
    dt = config['simulation']['dt']
    ego_speed = 0.0
    results = []

    for row in sensor_data:
        time = float(row['time'])
        lead_speed = row['lead_speed'] if row['lead_speed'] else None
        distance = row['distance'] if row['distance'] else None

        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)

        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance if distance else ''
        }
        results.append(result)

    return results


def tune_parameters(config, sensor_data):
    """
    Tune PID parameters using grid search.

    Args:
        config (dict): Configuration
        sensor_data (list): Sensor data

    Returns:
        dict: Best PID gains
    """
    print("Starting PID parameter tuning...")

    # Parameter ranges
    kp_speed_range = np.linspace(0.5, 5.0, 10)
    ki_speed_range = np.linspace(0.0, 1.0, 6)
    kd_speed_range = np.linspace(0.0, 1.0, 6)

    kp_dist_range = np.linspace(0.5, 5.0, 10)
    ki_dist_range = np.linspace(0.0, 1.0, 6)
    kd_dist_range = np.linspace(0.0, 1.0, 6)

    best_score = float('inf')
    best_gains = None

    total_combinations = len(kp_speed_range) * len(ki_speed_range) * len(kd_speed_range) * \
                       len(kp_dist_range) * len(ki_dist_range) * len(kd_dist_range)

    print(f"Testing {total_combinations} parameter combinations...")

    combination_count = 0

    for kp_s in kp_speed_range:
        for ki_s in ki_speed_range:
            for kd_s in kd_speed_range:
                for kp_d in kp_dist_range:
                    for ki_d in ki_dist_range:
                        for kd_d in kd_dist_range:
                            combination_count += 1

                            if combination_count % 100 == 0:
                                print(f"  Progress: {combination_count}/{total_combinations}")

                            pid_gains = {
                                'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
                            }

                            try:
                                results = run_simulation(config, sensor_data, pid_gains)
                                metrics = evaluate_performance(results, config)

                                if metrics['score'] < best_score:
                                    best_score = metrics['score']
                                    best_gains = pid_gains
                                    print(f"  New best score: {best_score:.2f}")
                            except Exception as e:
                                continue

    print(f"\nTuning complete!")
    print(f"Best score: {best_score:.2f}")
    print(f"Best gains: {best_gains}")

    return best_gains


def main():
    """Main tuning function."""
    # Load configuration
    config = load_config('vehicle_params.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Tune parameters
    best_gains = tune_parameters(config, sensor_data)

    # Save results
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_gains, f, default_flow_style=False)

    print(f"\nBest PID gains saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

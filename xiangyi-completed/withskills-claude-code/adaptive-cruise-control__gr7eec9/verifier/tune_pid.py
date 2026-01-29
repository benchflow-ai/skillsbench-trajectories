"""PID Parameter Tuning for Adaptive Cruise Control."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def evaluate_pid_gains(kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist, config, sensor_data):
    """
    Evaluate PID gains against performance metrics.

    Returns:
        Score (lower is better)
    """
    # Update config with test gains
    test_config = config.copy()
    test_config['pid_speed'] = {'kp': kp_speed, 'ki': ki_speed, 'kd': kd_speed}
    test_config['pid_distance'] = {'kp': kp_dist, 'ki': ki_dist, 'kd': kd_dist}

    acc = AdaptiveCruiseControl(test_config)
    dt = config['simulation']['dt']

    # Metrics tracking
    speed_errors = []
    distance_errors = []
    accelerations = []
    min_distances = []
    overshoot = False
    max_speed = 0.0

    ego_speed = 0.0
    settled_at = None
    set_speed = config['acc_settings']['set_speed']

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)

        # Simulate speed update (simple euler integration)
        ego_speed = max(0.0, min(ego_speed + accel_cmd * dt, 50.0))

        speed_error = set_speed - ego_speed
        speed_errors.append(abs(speed_error))

        if distance is not None:
            distance_errors.append(abs(dist_err) if dist_err is not None else 0.0)
            min_distances.append(distance)

        accelerations.append(abs(accel_cmd))
        max_speed = max(max_speed, ego_speed)

        # Check for overshoot in cruise phase
        if lead_speed is None and ego_speed > set_speed * 1.05:
            overshoot = True

        # Track when speed settles
        if lead_speed is None and abs(speed_error) < 0.5 and settled_at is None:
            settled_at = time

    # Calculate metrics
    avg_speed_error = np.mean(speed_errors) if speed_errors else float('inf')
    avg_distance_error = np.mean(distance_errors) if distance_errors else 0.0
    min_distance_val = min(min_distances) if min_distances else 0.0

    # Penalties for constraint violations
    penalty = 0.0
    if overshoot:
        penalty += 100.0
    if min_distance_val < 5.0:
        penalty += 50.0 * (5.0 - min_distance_val)
    if avg_distance_error > 2.0:
        penalty += 20.0 * (avg_distance_error - 2.0)

    # Settling time penalty (prefer < 10s)
    if settled_at is None or settled_at > 10.0:
        penalty += 30.0

    # Overall score (minimize)
    score = avg_speed_error * 10.0 + avg_distance_error * 5.0 + penalty

    return score


def grid_search_tune(config, sensor_data):
    """
    Grid search for PID parameters.

    Returns:
        Best parameters dictionary
    """
    # Parameter ranges
    kp_range = np.linspace(1.0, 5.0, 8)  # (0, 10) - higher for better response
    ki_range = np.linspace(0.0, 2.0, 6)  # [0, 5)
    kd_range = np.linspace(0.0, 1.5, 5)  # [0, 5)

    best_score = float('inf')
    best_params = None

    print("Starting grid search for PID tuning (Speed Controller)...")
    iteration = 0
    total = len(kp_range) * len(ki_range) * len(kd_range) * 2  # 2 PIDs

    # Tune speed controller first
    for kp_s in kp_range:
        for ki_s in ki_range:
            for kd_s in kd_range:
                # Evaluate speed controller
                score = evaluate_pid_gains(kp_s, ki_s, kd_s, 1.0, 0.2, 0.2, config, sensor_data)

                iteration += 1
                if iteration % 20 == 0:
                    print(f"  Progress: {iteration}/{total}, Best score: {best_score:.4f}")

                if score < best_score:
                    best_score = score
                    best_params = {
                        'pid_speed': {'kp': float(kp_s), 'ki': float(ki_s), 'kd': float(kd_s)},
                        'pid_distance': {'kp': 1.0, 'ki': 0.2, 'kd': 0.2},
                    }

    # Fine-tune distance controller
    print("Fine-tuning distance controller...")
    kp_dist_range = np.linspace(0.5, 3.0, 7)
    ki_dist_range = np.linspace(0.0, 1.0, 5)
    kd_dist_range = np.linspace(0.0, 1.0, 5)

    for kp_d in kp_dist_range:
        for ki_d in ki_dist_range:
            for kd_d in kd_dist_range:
                score = evaluate_pid_gains(
                    best_params['pid_speed']['kp'],
                    best_params['pid_speed']['ki'],
                    best_params['pid_speed']['kd'],
                    kp_d,
                    ki_d,
                    kd_d,
                    config,
                    sensor_data,
                )

                iteration += 1
                if iteration % 10 == 0:
                    print(f"  Progress: {iteration}/{total}, Best score: {best_score:.4f}")

                if score < best_score:
                    best_score = score
                    best_params = {
                        'pid_speed': best_params['pid_speed'],
                        'pid_distance': {'kp': float(kp_d), 'ki': float(ki_d), 'kd': float(kd_d)},
                    }

    return best_params, best_score


def main():
    """Load config, sensor data, and perform tuning."""
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')

    # Perform tuning
    best_params, best_score = grid_search_tune(config, sensor_data)

    # Save results
    tuning_results = {
        'pid_speed': best_params['pid_speed'],
        'pid_distance': best_params['pid_distance'],
        'best_score': float(best_score),
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print(f"\nTuning complete!")
    print(f"Best score: {best_score:.4f}")
    print(f"Speed PID: kp={best_params['pid_speed']['kp']:.4f}, "
          f"ki={best_params['pid_speed']['ki']:.4f}, "
          f"kd={best_params['pid_speed']['kd']:.4f}")
    print(f"Distance PID: kp={best_params['pid_distance']['kp']:.4f}, "
          f"ki={best_params['pid_distance']['ki']:.4f}, "
          f"kd={best_params['pid_distance']['kd']:.4f}")
    print(f"\nResults saved to /root/tuning_results.yaml")


if __name__ == '__main__':
    main()

"""Improved PID parameter tuning for ACC system - focused on performance targets."""

import csv
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def load_sensor_data(csv_path):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = (
                float(row["lead_speed"]) if row["lead_speed"].strip() else None
            )
            distance = float(row["distance"]) if row["distance"].strip() else None
            data.append(
                {"time": time, "ego_speed": ego_speed, "lead_speed": lead_speed, "distance": distance}
            )
    return data


def evaluate_pid_parameters(kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist,
                             config, sensor_data, dt):
    """
    Evaluate PID parameters based on target performance metrics.

    Returns a tuple: (overall_score, metrics)
    Lower score is better.
    """
    # Create a copy of config with test parameters
    test_config = config.copy()
    test_config["pid_speed"] = {"kp": kp_speed, "ki": ki_speed, "kd": kd_speed}
    test_config["pid_distance"] = {"kp": kp_dist, "ki": ki_dist, "kd": kd_dist}

    acc = AdaptiveCruiseControl(test_config)

    ego_speed = 0.0
    cruise_speeds = []
    follow_distance_errors = []
    accelerations = []

    set_speed = config['acc_settings']['set_speed']

    for i, data_point in enumerate(sensor_data):
        lead_speed = data_point["lead_speed"]
        distance = data_point["distance"]

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        accelerations.append(accel_cmd)

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Track cruise phase metrics (first 30 seconds, no lead vehicle)
        if data_point["time"] < 30.0:
            cruise_speeds.append(ego_speed)

        # Track follow phase metrics - abs value for error tracking
        if dist_error is not None:
            follow_distance_errors.append(abs(dist_error))

    # Performance scoring based on targets
    score = 0.0

    # Cruise phase: target speed rise time < 10s
    speed_rise_time = None
    target_95pct = set_speed * 0.95
    for i, speed in enumerate(cruise_speeds):
        if speed >= target_95pct:
            speed_rise_time = i * dt
            break

    if speed_rise_time is not None:
        if speed_rise_time < 10.0:
            rise_time_penalty = 0  # Good
        else:
            rise_time_penalty = (speed_rise_time - 10.0) * 10  # Penalize slow rise
    else:
        rise_time_penalty = 10000  # Failed to reach target

    score += rise_time_penalty

    # Cruise phase: target overshoot < 5%
    max_cruise_speed = max(cruise_speeds) if cruise_speeds else 0
    overshoot = (max_cruise_speed - set_speed) / set_speed * 100 if set_speed > 0 else 0

    if overshoot <= 5:
        overshoot_penalty = 0
    else:
        overshoot_penalty = (overshoot - 5) * 50  # Heavy penalty for excessive overshoot

    score += overshoot_penalty

    # Cruise phase: steady-state error < 0.5 m/s (last 5 seconds)
    cruise_ss = [s for i, s in enumerate(cruise_speeds) if (i * dt) >= 25.0]
    if cruise_ss:
        cruise_ss_error = abs(sum(cruise_ss) / len(cruise_ss) - set_speed)
    else:
        cruise_ss_error = abs(max_cruise_speed - set_speed)

    if cruise_ss_error <= 0.5:
        ss_penalty = 0
    else:
        ss_penalty = (cruise_ss_error - 0.5) * 100

    score += ss_penalty

    # Follow phase: distance steady-state error < 2m (last 30 seconds)
    if follow_distance_errors:
        dist_errors_ss = follow_distance_errors[-300:]  # Last 30 seconds
        if dist_errors_ss:
            dist_ss_error = np.mean(np.abs(dist_errors_ss))
        else:
            dist_ss_error = 0
    else:
        dist_ss_error = 0
        return 10000, {}

    if dist_ss_error <= 2.0:
        dist_ss_penalty = 0
    else:
        dist_ss_penalty = (dist_ss_error - 2.0) * 50

    score += dist_ss_penalty

    # Jerk penalty (smoothness)
    accel_diffs = [abs(accelerations[i+1] - accelerations[i]) for i in range(len(accelerations)-1)]
    avg_jerk = np.mean(accel_diffs) if accel_diffs else 0
    jerk_penalty = avg_jerk * 10

    score += jerk_penalty

    metrics = {
        "speed_rise_time": speed_rise_time,
        "overshoot": overshoot,
        "cruise_ss_error": cruise_ss_error,
        "distance_ss_error": dist_ss_error,
        "avg_jerk": avg_jerk,
        "overall_score": score
    }

    return score, metrics


def tune_pid_parameters(config_path, sensor_data_path, output_yaml_path):
    """
    Tune PID parameters using grid search focused on performance targets.
    """
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_data_path)
    dt = config["simulation"]["dt"]

    print("Starting PID tuning with performance-based cost function...")

    # Speed controller tuning - focus on reaching set speed
    best_score_speed = float('inf')
    best_params_speed = None

    print("\nTuning speed controller...")
    # Grid for speed: needs to accelerate to 30 m/s in < 10 seconds
    for kp in np.linspace(1.0, 3.0, 6):
        for ki in np.linspace(0.01, 0.2, 5):
            for kd in np.linspace(0.1, 0.5, 5):
                score, metrics = evaluate_pid_parameters(
                    kp, ki, kd, 0.5, 0.1, 0.2,  # Use reasonable distance params
                    config, sensor_data, dt
                )
                if score < best_score_speed:
                    best_score_speed = score
                    best_params_speed = (kp, ki, kd)
                    print(f"  Speed: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}")
                    print(f"    Rise time: {metrics['speed_rise_time']:.2f}s, Overshoot: {metrics['overshoot']:.2f}%, SS error: {metrics['cruise_ss_error']:.3f} m/s")
                    print(f"    Score: {score:.2f}")

    print(f"\nBest speed parameters found: kp={best_params_speed[0]:.3f}, ki={best_params_speed[1]:.3f}, kd={best_params_speed[2]:.3f}")

    # Fine-tune around best
    print("\nFine-tuning speed controller...")
    kp_best, ki_best, kd_best = best_params_speed
    for kp in np.linspace(max(0.5, kp_best - 0.5), min(5.0, kp_best + 0.5), 5):
        for ki in np.linspace(max(0.01, ki_best - 0.1), min(1.0, ki_best + 0.1), 5):
            for kd in np.linspace(max(0.0, kd_best - 0.2), min(2.0, kd_best + 0.2), 5):
                score, metrics = evaluate_pid_parameters(
                    kp, ki, kd, 0.5, 0.1, 0.2,
                    config, sensor_data, dt
                )
                if score < best_score_speed:
                    best_score_speed = score
                    best_params_speed = (kp, ki, kd)
                    print(f"  Speed: kp={kp:.4f}, ki={ki:.4f}, kd={kd:.4f}, score={score:.2f}")

    # Distance controller tuning
    best_score_dist = float('inf')
    best_params_dist = None

    print(f"\nTuning distance controller (using best speed params: {best_params_speed})...")
    for kp in np.linspace(0.5, 3.0, 6):
        for ki in np.linspace(0.01, 0.5, 5):
            for kd in np.linspace(0.1, 0.5, 5):
                score, metrics = evaluate_pid_parameters(
                    best_params_speed[0], best_params_speed[1], best_params_speed[2],
                    kp, ki, kd,
                    config, sensor_data, dt
                )
                if score < best_score_dist:
                    best_score_dist = score
                    best_params_dist = (kp, ki, kd)
                    print(f"  Distance: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}")
                    print(f"    Distance SS error: {metrics['distance_ss_error']:.2f}m, Score: {score:.2f}")

    print(f"\nBest distance parameters found: kp={best_params_dist[0]:.3f}, ki={best_params_dist[1]:.3f}, kd={best_params_dist[2]:.3f}")

    # Fine-tune around best
    print("\nFine-tuning distance controller...")
    kp_best, ki_best, kd_best = best_params_dist
    for kp in np.linspace(max(0.1, kp_best - 0.5), min(10.0, kp_best + 0.5), 5):
        for ki in np.linspace(max(0.01, ki_best - 0.15), min(1.0, ki_best + 0.15), 5):
            for kd in np.linspace(max(0.0, kd_best - 0.2), min(2.0, kd_best + 0.2), 5):
                score, metrics = evaluate_pid_parameters(
                    best_params_speed[0], best_params_speed[1], best_params_speed[2],
                    kp, ki, kd,
                    config, sensor_data, dt
                )
                if score < best_score_dist:
                    best_score_dist = score
                    best_params_dist = (kp, ki, kd)
                    print(f"  Distance: kp={kp:.4f}, ki={ki:.4f}, kd={kd:.4f}, score={score:.2f}")

    # Save tuning results
    tuning_results = {
        "pid_speed": {
            "kp": float(round(best_params_speed[0], 4)),
            "ki": float(round(best_params_speed[1], 4)),
            "kd": float(round(best_params_speed[2], 4)),
        },
        "pid_distance": {
            "kp": float(round(best_params_dist[0], 4)),
            "ki": float(round(best_params_dist[1], 4)),
            "kd": float(round(best_params_dist[2], 4)),
        },
    }

    with open(output_yaml_path, "w") as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print(f"\nTuning complete!")
    print(f"Final PID Speed: kp={tuning_results['pid_speed']['kp']}, ki={tuning_results['pid_speed']['ki']}, kd={tuning_results['pid_speed']['kd']}")
    print(f"Final PID Distance: kp={tuning_results['pid_distance']['kp']}, ki={tuning_results['pid_distance']['ki']}, kd={tuning_results['pid_distance']['kd']}")

    return tuning_results


if __name__ == "__main__":
    tune_pid_parameters(
        "/root/vehicle_params.yaml",
        "/root/sensor_data.csv",
        "/root/tuning_results.yaml",
    )

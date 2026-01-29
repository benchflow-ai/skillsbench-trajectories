"""PID parameter tuning for ACC system."""

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
    Evaluate PID parameters on the simulation data.

    Returns a tuple: (overall_score, metrics)
    Lower score is better.
    """
    # Create a copy of config with test parameters
    test_config = config.copy()
    test_config["pid_speed"] = {"kp": kp_speed, "ki": ki_speed, "kd": kd_speed}
    test_config["pid_distance"] = {"kp": kp_dist, "ki": ki_dist, "kd": kd_dist}

    acc = AdaptiveCruiseControl(test_config)

    ego_speed = 0.0
    speed_errors = []
    distance_errors = []
    accel_commands = []

    for i, data_point in enumerate(sensor_data):
        lead_speed = data_point["lead_speed"]
        distance = data_point["distance"]

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        accel_commands.append(accel_cmd)

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Track errors
        if lead_speed is not None:
            speed_errors.append(lead_speed - ego_speed)
        else:
            # Cruising - error is difference from set speed
            speed_errors.append(config["acc_settings"]["set_speed"] - ego_speed)

        if dist_error is not None:
            distance_errors.append(dist_error)

    # Compute metrics
    speed_mse = np.mean(np.array(speed_errors) ** 2)
    dist_mse = np.mean(np.array(distance_errors) ** 2) if distance_errors else 0
    accel_smoothness = np.mean(np.diff(accel_commands) ** 2)

    # Weighted cost function
    # Prioritize: speed accuracy (40%), distance accuracy (40%), smoothness (20%)
    overall_score = 0.4 * speed_mse + 0.4 * dist_mse + 0.2 * accel_smoothness

    metrics = {
        "speed_mse": speed_mse,
        "distance_mse": dist_mse,
        "accel_smoothness": accel_smoothness,
        "overall_score": overall_score
    }

    return overall_score, metrics


def tune_pid_parameters(config_path, sensor_data_path, output_yaml_path):
    """
    Tune PID parameters using grid search.

    Tuning ranges:
    - kp: (0, 10)
    - ki: [0, 5)
    - kd: [0, 5)
    """
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_data_path)
    dt = config["simulation"]["dt"]

    print("Starting PID tuning...")

    # Grid search with coarse then fine tuning
    # Speed controller tuning
    best_score_speed = float('inf')
    best_params_speed = None

    print("Tuning speed controller...")
    # Coarse grid - start with wider range for speed controller
    for kp in np.linspace(0.5, 5.0, 10):
        for ki in np.linspace(0.0, 1.0, 6):
            for kd in np.linspace(0.0, 1.0, 6):
                score, metrics = evaluate_pid_parameters(
                    kp, ki, kd, 0.1, 0.01, 0.0,  # Use default distance params
                    config, sensor_data, dt
                )
                if score < best_score_speed:
                    best_score_speed = score
                    best_params_speed = (kp, ki, kd)
                    print(f"  Speed: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}, score={score:.6f}")

    print(f"\nBest speed parameters: kp={best_params_speed[0]:.3f}, ki={best_params_speed[1]:.3f}, kd={best_params_speed[2]:.3f}")
    print(f"Best speed score: {best_score_speed:.6f}")

    # Fine tuning around best speed parameters
    print("\nFine-tuning speed controller...")
    kp_best, ki_best, kd_best = best_params_speed
    for kp in np.linspace(max(0.1, kp_best - 1.0), min(10, kp_best + 1.0), 5):
        for ki in np.linspace(max(0, ki_best - 0.3), min(5, ki_best + 0.3), 5):
            for kd in np.linspace(max(0, kd_best - 0.3), min(5, kd_best + 0.3), 5):
                score, metrics = evaluate_pid_parameters(
                    kp, ki, kd, 0.1, 0.01, 0.0,
                    config, sensor_data, dt
                )
                if score < best_score_speed:
                    best_score_speed = score
                    best_params_speed = (kp, ki, kd)
                    print(f"  Speed: kp={kp:.4f}, ki={ki:.4f}, kd={kd:.4f}, score={score:.6f}")

    # Distance controller tuning (using best speed params)
    best_score_dist = float('inf')
    best_params_dist = None

    print("\nTuning distance controller...")
    # Coarse grid - wider range for distance controller
    for kp in np.linspace(0.5, 5.0, 10):
        for ki in np.linspace(0.0, 1.0, 6):
            for kd in np.linspace(0.0, 1.0, 6):
                score, metrics = evaluate_pid_parameters(
                    best_params_speed[0], best_params_speed[1], best_params_speed[2],
                    kp, ki, kd,
                    config, sensor_data, dt
                )
                if score < best_score_dist:
                    best_score_dist = score
                    best_params_dist = (kp, ki, kd)
                    print(f"  Distance: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}, score={score:.6f}")

    print(f"\nBest distance parameters: kp={best_params_dist[0]:.3f}, ki={best_params_dist[1]:.3f}, kd={best_params_dist[2]:.3f}")
    print(f"Best distance score: {best_score_dist:.6f}")

    # Fine tuning around best distance parameters
    print("\nFine-tuning distance controller...")
    kp_best, ki_best, kd_best = best_params_dist
    for kp in np.linspace(max(0.1, kp_best - 1.0), min(10, kp_best + 1.0), 5):
        for ki in np.linspace(max(0, ki_best - 0.3), min(5, ki_best + 0.3), 5):
            for kd in np.linspace(max(0, kd_best - 0.3), min(5, kd_best + 0.3), 5):
                score, metrics = evaluate_pid_parameters(
                    best_params_speed[0], best_params_speed[1], best_params_speed[2],
                    kp, ki, kd,
                    config, sensor_data, dt
                )
                if score < best_score_dist:
                    best_score_dist = score
                    best_params_dist = (kp, ki, kd)
                    print(f"  Distance: kp={kp:.4f}, ki={ki:.4f}, kd={kd:.4f}, score={score:.6f}")

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

    print(f"\nTuning results saved to {output_yaml_path}")
    print(tuning_results)

    return tuning_results


if __name__ == "__main__":
    tune_pid_parameters(
        "/root/vehicle_params.yaml",
        "/root/sensor_data.csv",
        "/root/tuning_results.yaml",
    )

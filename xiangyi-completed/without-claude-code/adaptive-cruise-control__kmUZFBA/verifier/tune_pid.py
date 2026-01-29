"""PID tuning for ACC system using sensor data."""

import csv
import yaml
from pid_controller import PIDController


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(
                {
                    "time": float(row["time"]),
                    "ego_speed_ref": float(row["ego_speed"]),
                    "lead_speed": (
                        float(row["lead_speed"]) if row["lead_speed"].strip() else None
                    ),
                    "distance": (
                        float(row["distance"]) if row["distance"].strip() else None
                    ),
                }
            )
    return data


def simulate_with_acc(sensor_data, config, dt=0.1):
    """
    Simulate ACC system with given config and return metrics.

    Returns: dict with performance metrics
    """
    from acc_system import AdaptiveCruiseControl

    acc = AdaptiveCruiseControl(config)
    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]
    set_speed = config["acc_settings"]["set_speed"]
    time_headway = config["acc_settings"]["time_headway"]
    min_distance = config["acc_settings"]["min_distance"]

    ego_speed = 0.0

    # Cruise phase metrics
    cruise_speeds = []
    cruise_times = []
    max_speed = 0.0
    rise_time_90 = None

    # Follow phase metrics
    distance_errors = []
    min_dist_observed = float("inf")

    for sensor_row in sensor_data:
        time = sensor_row["time"]
        lead_speed = sensor_row["lead_speed"]
        distance = sensor_row["distance"]

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Clamp and integrate
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Collect cruise phase metrics (first 30 seconds, no lead vehicle)
        if time <= 30.0:
            cruise_speeds.append(ego_speed)
            cruise_times.append(time)
            max_speed = max(max_speed, ego_speed)

            if rise_time_90 is None and ego_speed >= 0.9 * set_speed:
                rise_time_90 = time

        # Collect follow phase metrics (after 30s, lead vehicle present)
        if time >= 50.0 and lead_speed is not None and distance is not None:
            desired_distance = time_headway * ego_speed + min_distance
            actual_error = desired_distance - distance
            distance_errors.append(abs(actual_error))
            min_dist_observed = min(min_dist_observed, distance)

    # Calculate metrics
    metrics = {
        "rise_time": rise_time_90 if rise_time_90 else float("inf"),
        "overshoot": max(0, (max_speed - set_speed) / set_speed * 100),
        "cruise_sse": abs(set_speed - cruise_speeds[-1]) if cruise_speeds else float("inf"),
        "distance_sse": sum(distance_errors) / len(distance_errors) if distance_errors else float("inf"),
        "min_distance": min_dist_observed,
    }

    return metrics


def tune_pids(config_file, sensor_file):
    """Tune PID parameters for speed and distance control."""
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    print("Tuning PID parameters...")

    # Grid search parameters
    kp_values = [0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    ki_values = [0.0, 0.01, 0.05, 0.1, 0.2]
    kd_values = [0.0, 0.1, 0.5, 1.0, 2.0]

    # Tune speed control
    print("\nTuning speed control PID...")
    best_speed_params = None
    best_speed_score = float("inf")

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                test_config = load_config(config_file)
                test_config["pid_speed"] = {"kp": kp, "ki": ki, "kd": kd}

                metrics = simulate_with_acc(sensor_data, test_config)

                # Score: penalize violations of targets
                score = 0
                if metrics["rise_time"] <= 10:
                    score += (metrics["rise_time"] / 10) ** 2
                else:
                    score += 1 + (metrics["rise_time"] - 10) / 10

                if metrics["overshoot"] <= 5:
                    score += (metrics["overshoot"] / 5) ** 2
                else:
                    score += 1 + (metrics["overshoot"] - 5) / 5

                if metrics["cruise_sse"] <= 0.5:
                    score += (metrics["cruise_sse"] / 0.5) ** 2
                else:
                    score += 1 + (metrics["cruise_sse"] - 0.5) / 0.5

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_params = (kp, ki, kd)
                    best_speed_metrics = metrics

    print(f"Best speed control: kp={best_speed_params[0]}, ki={best_speed_params[1]}, kd={best_speed_params[2]}")
    print(f"  Rise time: {best_speed_metrics['rise_time']:.2f}s, Overshoot: {best_speed_metrics['overshoot']:.2f}%, SSE: {best_speed_metrics['cruise_sse']:.4f} m/s")

    # Tune distance control
    print("\nTuning distance control PID...")
    best_distance_params = None
    best_distance_score = float("inf")

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                test_config = load_config(config_file)
                test_config["pid_distance"] = {"kp": kp, "ki": ki, "kd": kd}

                metrics = simulate_with_acc(sensor_data, test_config)

                # Score for distance control
                score = 0
                if metrics["distance_sse"] <= 2:
                    score += (metrics["distance_sse"] / 2) ** 2
                else:
                    score += 1 + (metrics["distance_sse"] - 2) / 2

                if metrics["min_distance"] >= 5:
                    score += 0
                else:
                    score += 2 * (5 - metrics["min_distance"])

                if score < best_distance_score:
                    best_distance_score = score
                    best_distance_params = (kp, ki, kd)
                    best_distance_metrics = metrics

    print(f"Best distance control: kp={best_distance_params[0]}, ki={best_distance_params[1]}, kd={best_distance_params[2]}")
    print(f"  Distance SSE: {best_distance_metrics['distance_sse']:.3f}m, Min distance: {best_distance_metrics['min_distance']:.2f}m")

    # Save tuning results
    tuning_results = {
        "pid_speed": {
            "kp": float(best_speed_params[0]),
            "ki": float(best_speed_params[1]),
            "kd": float(best_speed_params[2]),
        },
        "pid_distance": {
            "kp": float(best_distance_params[0]),
            "ki": float(best_distance_params[1]),
            "kd": float(best_distance_params[2]),
        },
    }

    with open("tuning_results.yaml", "w") as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")
    return tuning_results


if __name__ == "__main__":
    tune_pids("vehicle_params.yaml", "sensor_data.csv")

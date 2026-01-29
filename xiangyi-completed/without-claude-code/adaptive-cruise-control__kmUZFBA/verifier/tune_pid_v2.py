"""Improved PID tuning focused on distance control."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


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
                    "lead_speed": (
                        float(row["lead_speed"]) if row["lead_speed"].strip() else None
                    ),
                    "distance": (
                        float(row["distance"]) if row["distance"].strip() else None
                    ),
                }
            )
    return data


def evaluate_distance_control(sensor_data, kp, ki, kd, config, dt=0.1):
    """Evaluate distance control performance."""
    acc = AdaptiveCruiseControl(config)
    acc.pid_distance = acc.PIDController = __import__("pid_controller").PIDController(kp, ki, kd)

    # Manual setup
    from pid_controller import PIDController
    acc.pid_distance = PIDController(kp, ki, kd)

    ego_speed = 30.0  # Start at cruise speed to evaluate follow phase

    time_headway = config["acc_settings"]["time_headway"]
    min_distance = config["acc_settings"]["min_distance"]

    distance_errors = []
    min_dist = float("inf")
    accel_violations = 0

    for sensor_row in sensor_data:
        time = sensor_row["time"]
        lead_speed = sensor_row["lead_speed"]
        distance = sensor_row["distance"]

        if lead_speed is not None and distance is not None and time >= 30:
            # Calculate desired distance
            desired_distance = time_headway * ego_speed + min_distance
            distance_error = desired_distance - distance

            # Compute control
            accel_cmd = acc.pid_distance.compute(distance_error, dt)
            accel_cmd = max(-8.0, min(3.0, accel_cmd))

            # Update speed
            ego_speed = max(0.0, ego_speed + accel_cmd * dt)

            min_dist = min(min_dist, distance)

            # Collect errors for steady-state (after transient)
            if time >= 50:
                distance_errors.append(abs(distance_error))

            # Check acceleration limits
            if accel_cmd < -8.0 or accel_cmd > 3.0:
                accel_violations += 1

    sse = sum(distance_errors) / len(distance_errors) if distance_errors else float("inf")

    return sse, min_dist, accel_violations


def tune_distance(config_file, sensor_file):
    """Focused tuning on distance control."""
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)

    print("Focused distance control tuning...")

    # More aggressive tuning for distance control
    best_params = None
    best_score = float("inf")

    # Grid search with wider range
    for kp in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        for ki in [0.01, 0.02, 0.05, 0.1, 0.15, 0.2]:
            for kd in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
                sse, min_dist, violations = evaluate_distance_control(
                    sensor_data, kp, ki, kd, config
                )

                # Score: prefer low SSE and safe minimum distance
                score = 0
                if sse <= 2:
                    score += (sse / 2) ** 2 * 50
                else:
                    score += 50 + 20 * (sse - 2)

                if min_dist >= 5:
                    score += 0
                else:
                    score += 30 * (5 - min_dist) ** 2

                score += violations  # Penalize violations

                if score < best_score:
                    best_score = score
                    best_params = (kp, ki, kd)
                    print(f"  kp={kp:.1f}, ki={ki:.2f}, kd={kd:.1f} -> SSE={sse:.2f}m, min_dist={min_dist:.2f}m, score={score:.1f}")

    print(f"\nBest distance params: kp={best_params[0]}, ki={best_params[1]}, kd={best_params[2]}")

    # Load existing speed tuning and update distance tuning
    with open("tuning_results.yaml") as f:
        results = yaml.safe_load(f)

    results["pid_distance"] = {
        "kp": float(best_params[0]),
        "ki": float(best_params[1]),
        "kd": float(best_params[2]),
    }

    with open("tuning_results.yaml", "w") as f:
        yaml.dump(results, f, default_flow_style=False)

    print("Updated tuning_results.yaml")


if __name__ == "__main__":
    tune_distance("vehicle_params.yaml", "sensor_data.csv")

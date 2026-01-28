"""PID parameter tuning for ACC system."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_path):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = row["lead_speed"]
            distance = row["distance"]

            lead_speed = float(lead_speed) if lead_speed.strip() else None
            distance = float(distance) if distance.strip() else None

            data.append(
                {
                    "time": time,
                    "ego_speed": ego_speed,
                    "lead_speed": lead_speed,
                    "distance": distance,
                }
            )
    return data


def evaluate_tuning(config, pid_speed_gains, pid_distance_gains, sensor_data):
    """
    Evaluate PID gains on the sensor data.

    Returns a score based on performance metrics.
    """
    config_test = config.copy()
    config_test["pid_speed"] = pid_speed_gains
    config_test["pid_distance"] = pid_distance_gains

    acc = AdaptiveCruiseControl(config_test)
    dt = config.get("simulation", {}).get("dt", 0.1)
    set_speed = config.get("acc_settings", {}).get("set_speed", 30.0)
    min_distance = config.get("acc_settings", {}).get("min_distance", 10.0)

    ego_speed = 0.0
    speed_errors = []
    distance_errors = []
    min_distances = []
    emergency_triggers = 0

    for sensor_point in sensor_data:
        lead_speed = sensor_point["lead_speed"]
        distance = sensor_point["distance"]

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Track metrics
        if lead_speed is None:
            speed_errors.append(abs(set_speed - ego_speed))

        if distance is not None:
            min_distances.append(distance)
            if distance_error is not None:
                distance_errors.append(abs(distance_error))

        if mode == "emergency":
            emergency_triggers += 1

    # Calculate score (lower is better)
    score = 0.0

    # Speed control metrics (cruise phase)
    if speed_errors:
        avg_speed_error = sum(speed_errors) / len(speed_errors)
        score += avg_speed_error * 10

    # Distance control metrics
    if distance_errors:
        avg_distance_error = sum(distance_errors) / len(distance_errors)
        score += avg_distance_error * 5

    # Minimum distance safety metric
    if min_distances:
        min_gap = min(min_distances)
        if min_gap < min_distance:
            score += (min_distance - min_gap) * 20  # Penalty for violating min distance

    # Emergency braking penalty
    score += emergency_triggers * 100

    return score


def tune_pid_parameters(config_path, sensor_path):
    """
    Tune PID parameters using grid search with refinement.

    This is a simplified tuning that prioritizes safety and stability.
    """
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_path)

    print("Tuning PID parameters...")

    # Coarse grid search
    best_score = float("inf")
    best_speed_gains = None
    best_distance_gains = None

    # Speed controller: focus on smooth acceleration without overshoot
    kp_candidates = [0.2, 0.5, 0.8, 1.0]
    ki_candidates = [0.01, 0.05, 0.1]
    kd_candidates = [0.0, 0.1, 0.2]

    print("Coarse grid search...")
    for kp in kp_candidates:
        for ki in ki_candidates:
            for kd in kd_candidates:
                # Speed gains
                speed_gains = {"kp": kp, "ki": ki, "kd": kd}

                # Distance gains - typically need more aggressive control
                dist_gains = {"kp": 0.5, "ki": 0.05, "kd": 0.1}

                score = evaluate_tuning(config, speed_gains, dist_gains, sensor_data)

                if score < best_score:
                    best_score = score
                    best_speed_gains = speed_gains
                    best_distance_gains = dist_gains
                    print(
                        f"  New best: speed(kp={kp},ki={ki},kd={kd}) score={score:.2f}"
                    )

    # Fine-tune distance gains around best speed gains
    print("Fine-tuning distance controller...")
    kp_candidates_fine = [0.3, 0.4, 0.5, 0.6, 0.7]
    ki_candidates_fine = [0.02, 0.05, 0.08]
    kd_candidates_fine = [0.05, 0.1, 0.15]

    for kp in kp_candidates_fine:
        for ki in ki_candidates_fine:
            for kd in kd_candidates_fine:
                dist_gains = {"kp": kp, "ki": ki, "kd": kd}

                score = evaluate_tuning(
                    config, best_speed_gains, dist_gains, sensor_data
                )

                if score < best_score:
                    best_score = score
                    best_distance_gains = dist_gains
                    print(
                        f"  New best: distance(kp={kp},ki={ki},kd={kd}) score={score:.2f}"
                    )

    print(f"\nBest tuning found with score: {best_score:.4f}")
    print(f"Speed gains: {best_speed_gains}")
    print(f"Distance gains: {best_distance_gains}")

    return best_speed_gains, best_distance_gains


if __name__ == "__main__":
    speed_gains, distance_gains = tune_pid_parameters(
        "/root/vehicle_params.yaml", "/root/sensor_data.csv"
    )

    # Save tuning results
    tuning_results = {
        "pid_speed": speed_gains,
        "pid_distance": distance_gains,
    }

    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning results saved to /root/tuning_results.yaml")

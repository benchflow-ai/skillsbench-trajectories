"""
PID tuning for ACC system using grid search and metrics evaluation.
"""

import csv
import yaml
import math
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
                    "ego_speed": float(row["ego_speed"]),
                    "lead_speed": float(row["lead_speed"]) if row["lead_speed"] else None,
                    "distance": float(row["distance"]) if row["distance"] else None,
                }
            )
    return data


def run_simulation_with_gains(config, sensor_data, speed_gains, distance_gains):
    """Run simulation with given PID gains and return metrics."""
    # Create config copy with tuned gains
    tuned_config = config.copy()
    tuned_config["pid_speed"] = speed_gains
    tuned_config["pid_distance"] = distance_gains

    acc = AdaptiveCruiseControl(tuned_config)

    dt = config["simulation"]["dt"]
    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]
    set_speed = config["acc_settings"]["set_speed"]

    ego_speed = sensor_data[0]["ego_speed"]
    results = []

    for sensor in sensor_data:
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        results.append(
            {
                "time": sensor["time"],
                "ego_speed": ego_speed,
                "mode": mode,
                "accel": accel_cmd,
                "distance_error": distance_error,
                "distance": distance,
                "lead_speed": lead_speed,
            }
        )

    return calculate_metrics(results, set_speed, sensor_data)


def calculate_metrics(results, set_speed, sensor_data):
    """Calculate performance metrics from simulation results."""
    metrics = {
        "speed_errors": [],
        "distance_errors": [],
        "speeds": [],
        "cruise_speeds": [],
        "ttc_min": float("inf"),
        "safety_violations": 0,
    }

    for i, result in enumerate(results):
        sensor = sensor_data[i]
        time = result["time"]

        # Speed error in cruise mode
        if result["mode"] == "cruise":
            speed_error = abs(set_speed - result["ego_speed"])
            metrics["speed_errors"].append(speed_error)
            metrics["cruise_speeds"].append(result["ego_speed"])

        # Distance error in follow mode
        if result["mode"] == "follow" and result["distance_error"] is not None:
            metrics["distance_errors"].append(abs(result["distance_error"]))

            # Calculate TTC
            speed_diff = result["ego_speed"] - result["lead_speed"]
            if speed_diff > 0.01 and result["distance"] is not None:
                ttc = result["distance"] / speed_diff
                metrics["ttc_min"] = min(metrics["ttc_min"], ttc)

                # Check minimum distance safety
                if result["distance"] < 5.0:
                    metrics["safety_violations"] += 1

        metrics["speeds"].append(result["ego_speed"])

    # Compute aggregated metrics
    result_metrics = {
        "avg_speed_error": (
            sum(metrics["speed_errors"]) / len(metrics["speed_errors"])
            if metrics["speed_errors"]
            else 0.0
        ),
        "avg_distance_error": (
            sum(metrics["distance_errors"]) / len(metrics["distance_errors"])
            if metrics["distance_errors"]
            else 0.0
        ),
        "max_speed_error": max(metrics["speed_errors"]) if metrics["speed_errors"] else 0.0,
        "max_distance_error": max(metrics["distance_errors"]) if metrics["distance_errors"] else 0.0,
        "steady_state_speed": (
            sum(metrics["cruise_speeds"]) / len(metrics["cruise_speeds"])
            if metrics["cruise_speeds"]
            else 0.0
        ),
        "ttc_min": metrics["ttc_min"] if metrics["ttc_min"] != float("inf") else None,
        "safety_violations": metrics["safety_violations"],
    }

    return result_metrics


def objective_function(metrics):
    """
    Calculate fitness score. Lower is better.

    Weights:
    - Speed steady-state error (target <0.5 m/s)
    - Distance steady-state error (target <2m)
    - Safety violations (minimum distance >5m)
    """
    score = 0.0

    # Speed error term (weight=1.0)
    if metrics["avg_speed_error"] < 0.5:
        speed_penalty = metrics["avg_speed_error"]
    else:
        speed_penalty = metrics["avg_speed_error"] * 2.0  # Higher penalty for large errors

    # Distance error term (weight=1.0)
    if metrics["avg_distance_error"] is not None and metrics["avg_distance_error"] < 2.0:
        distance_penalty = metrics["avg_distance_error"]
    else:
        distance_penalty = (metrics["avg_distance_error"] * 2.0) if metrics["avg_distance_error"] else 0.0

    # Safety penalty
    safety_penalty = metrics["safety_violations"] * 100.0

    score = speed_penalty + distance_penalty + safety_penalty

    return score


def tune_pid_gains(config, sensor_data):
    """
    Tune PID gains using grid search.

    Ranges:
    - kp in (0, 10)
    - ki in [0, 5)
    - kd in [0, 5)
    """
    best_score = float("inf")
    best_gains = {
        "speed": {"kp": 0.1, "ki": 0.01, "kd": 0.0},
        "distance": {"kp": 0.1, "ki": 0.01, "kd": 0.0},
    }

    # Grid search with coarse and fine steps
    speed_kp_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    speed_ki_values = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2]
    speed_kd_values = [0.0, 0.1, 0.2, 0.5, 1.0]

    distance_kp_values = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    distance_ki_values = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2]
    distance_kd_values = [0.0, 0.5, 1.0, 1.5, 2.0]

    total_combinations = (
        len(speed_kp_values)
        * len(speed_ki_values)
        * len(speed_kd_values)
        * len(distance_kp_values)
        * len(distance_ki_values)
        * len(distance_kd_values)
    )

    print(f"Tuning PID gains (total combinations: {total_combinations})...")
    count = 0

    for speed_kp in speed_kp_values:
        for speed_ki in speed_ki_values:
            for speed_kd in speed_kd_values:
                for dist_kp in distance_kp_values:
                    for dist_ki in distance_ki_values:
                        for dist_kd in distance_kd_values:
                            count += 1
                            if count % 100 == 0:
                                print(f"  Progress: {count}/{total_combinations}")

                            speed_gains = {"kp": speed_kp, "ki": speed_ki, "kd": speed_kd}
                            distance_gains = {"kp": dist_kp, "ki": dist_ki, "kd": dist_kd}

                            try:
                                metrics = run_simulation_with_gains(
                                    config, sensor_data, speed_gains, distance_gains
                                )
                                score = objective_function(metrics)

                                if score < best_score:
                                    best_score = score
                                    best_gains = {"speed": speed_gains, "distance": distance_gains}
                                    best_metrics = metrics

                            except Exception as e:
                                print(f"    Error with kp={speed_kp}, ki={speed_ki}, kd={speed_kd}: {e}")

    print(f"Best score: {best_score:.4f}")
    print(f"Best speed gains: {best_gains['speed']}")
    print(f"Best distance gains: {best_gains['distance']}")
    print(f"Best metrics: {best_metrics}")

    return best_gains


if __name__ == "__main__":
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")

    tuned_gains = tune_pid_gains(config, sensor_data)

    # Save tuning results
    tuning_results = {
        "pid_speed": tuned_gains["speed"],
        "pid_distance": tuned_gains["distance"],
    }

    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("Tuning results saved to tuning_results.yaml")

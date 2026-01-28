"""
PID tuning script to find optimal parameters for ACC speed and distance control.
Uses a combination of heuristics and parameter sweep to find good PID gains.
"""

import csv
import math
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                "time": float(row["time"]),
                "ego_speed": float(row["ego_speed"]),
                "lead_speed": (
                    float(row["lead_speed"]) if row["lead_speed"].strip() else None
                ),
                "distance": (
                    float(row["distance"]) if row["distance"].strip() else None
                ),
            }
            data.append(record)
    return data


def simulate_with_pid(config, sensor_data, speed_pid, distance_pid):
    """
    Run simulation with given PID parameters and return performance metrics.

    Returns:
        Dict with metrics: speed_rise_time, speed_overshoot, speed_sse,
                          distance_sse, min_distance, emergency_count
    """
    # Update config with test PID parameters
    test_config = config.copy()
    test_config["pid_speed"] = speed_pid.copy()
    test_config["pid_distance"] = distance_pid.copy()

    # Initialize ACC system
    acc = AdaptiveCruiseControl(test_config)
    dt = test_config["simulation"]["dt"]

    # Simulation variables
    speeds = []
    speed_errors = []
    distance_errors = []
    min_distance_seen = float("inf")
    emergency_count = 0
    rise_time_idx = -1
    max_overshoot = 0.0

    set_speed = test_config["acc_settings"]["set_speed"]

    # Process sensor data
    for sensor in sensor_data:
        ego_speed = sensor["ego_speed"]
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        # Compute ACC output
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        speeds.append(ego_speed)
        speed_error = set_speed - ego_speed
        speed_errors.append(speed_error)

        if distance_error is not None:
            distance_errors.append(distance_error)
            min_distance_seen = min(min_distance_seen, distance)

        if mode == "emergency":
            emergency_count += 1

        # Track rise time (when speed first reaches 90% of set speed)
        if rise_time_idx == -1 and ego_speed >= 0.9 * set_speed:
            rise_time_idx = len(speeds) - 1

        # Track overshoot (max speed - set speed)
        if ego_speed > set_speed:
            max_overshoot = max(max_overshoot, ego_speed - set_speed)

    # Calculate metrics
    rise_time = (
        (rise_time_idx * dt) if rise_time_idx >= 0 else float("inf")
    )  # in seconds

    # Speed overshoot percentage
    speed_overshoot = (max_overshoot / set_speed) * 100 if set_speed > 0 else 0

    # Speed steady-state error (last 10 seconds)
    last_10s_idx = max(0, len(speeds) - int(10 / dt))
    speed_sse = (
        sum(abs(e) for e in speed_errors[last_10s_idx:]) / len(speed_errors[last_10s_idx:])
        if len(speed_errors[last_10s_idx:]) > 0
        else 0
    )

    # Distance steady-state error (last 10 seconds)
    if len(distance_errors) > 0:
        last_10s_idx_dist = max(0, len(distance_errors) - int(10 / dt))
        distance_sse = (
            sum(abs(e) for e in distance_errors[last_10s_idx_dist:])
            / len(distance_errors[last_10s_idx_dist:])
            if len(distance_errors[last_10s_idx_dist:]) > 0
            else 0
        )
    else:
        distance_sse = 0

    # Minimum distance during follow mode
    if min_distance_seen == float("inf"):
        min_distance_seen = None

    return {
        "speed_rise_time": rise_time,
        "speed_overshoot": speed_overshoot,
        "speed_sse": speed_sse,
        "distance_sse": distance_sse,
        "min_distance": min_distance_seen,
        "emergency_count": emergency_count,
    }


def calculate_fitness(metrics):
    """
    Calculate fitness score for tuning results.
    Lower score is better. Penalizes violations of targets.
    """
    score = 0.0

    # Target: rise time < 10s
    if metrics["speed_rise_time"] < 10.0:
        score += metrics["speed_rise_time"] * 0.5  # Prefer faster rise time
    else:
        score += 10.0 + (metrics["speed_rise_time"] - 10.0) * 5.0  # Heavy penalty

    # Target: overshoot < 5%
    if metrics["speed_overshoot"] < 5.0:
        score += metrics["speed_overshoot"] * 0.1
    else:
        score += 5.0 + (metrics["speed_overshoot"] - 5.0) * 2.0  # Penalty

    # Target: speed SSE < 0.5 m/s
    if metrics["speed_sse"] < 0.5:
        score += metrics["speed_sse"] * 5.0
    else:
        score += 0.5 + (metrics["speed_sse"] - 0.5) * 10.0  # Penalty

    # Target: distance SSE < 2m
    if metrics["distance_sse"] < 2.0:
        score += metrics["distance_sse"] * 0.5
    else:
        score += 2.0 + (metrics["distance_sse"] - 2.0) * 2.0  # Penalty

    # Target: min distance > 5m
    if metrics["min_distance"] is not None:
        if metrics["min_distance"] > 5.0:
            score += (metrics["min_distance"] - 5.0) * 0.01  # Small bonus for safety margin
        else:
            score += (5.0 - metrics["min_distance"]) * 10.0  # Heavy penalty for safety violation

    # Penalize emergency braking events
    score += metrics["emergency_count"] * 2.0

    return score


def grid_search_tuning(config, sensor_data):
    """
    Perform grid search to find good PID parameters.
    Searches in ranges: Kp=[0.5, 10.0], Ki=[0.0, 5.0], Kd=[0.0, 5.0]
    """
    best_score = float("inf")
    best_speed_pid = None
    best_distance_pid = None

    # Expanded grid search with wider ranges
    kp_values = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    ki_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    kd_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    print("Starting PID tuning with expanded search space...")

    # Tune speed controller
    print("Tuning speed controller...")
    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                speed_pid = {"kp": kp, "ki": ki, "kd": kd}
                distance_pid = {"kp": 2.0, "ki": 0.5, "kd": 1.0}  # Use reasonable initial guess

                metrics = simulate_with_pid(config, sensor_data, speed_pid, distance_pid)
                score = calculate_fitness(metrics)

                if score < best_score:
                    best_score = score
                    best_speed_pid = speed_pid.copy()
                    print(
                        f"  NEW BEST Speed PID Kp={kp:.1f} Ki={ki:.1f} Kd={kd:.1f}: "
                        f"score={score:.2f}, rise={metrics['speed_rise_time']:.1f}s, "
                        f"sse={metrics['speed_sse']:.3f}m/s"
                    )

    print(f"Best speed PID: {best_speed_pid}, score={best_score:.2f}\n")

    # Tune distance controller with best speed PID
    print("Tuning distance controller...")
    best_score = float("inf")
    best_distance_pid = None

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                distance_pid = {"kp": kp, "ki": ki, "kd": kd}

                metrics = simulate_with_pid(config, sensor_data, best_speed_pid, distance_pid)
                score = calculate_fitness(metrics)

                if score < best_score:
                    best_score = score
                    best_distance_pid = distance_pid.copy()
                    print(
                        f"  NEW BEST Distance PID Kp={kp:.1f} Ki={ki:.1f} Kd={kd:.1f}: "
                        f"score={score:.2f}, dist_sse={metrics['distance_sse']:.2f}m"
                    )

    print(f"Best distance PID: {best_distance_pid}, score={best_score:.2f}")

    return best_speed_pid, best_distance_pid


def save_tuning_results(speed_pid, distance_pid, output_path):
    """Save tuning results to YAML file."""
    results = {
        "pid_speed": {
            "kp": round(speed_pid["kp"], 4),
            "ki": round(speed_pid["ki"], 4),
            "kd": round(speed_pid["kd"], 4),
        },
        "pid_distance": {
            "kp": round(distance_pid["kp"], 4),
            "ki": round(distance_pid["ki"], 4),
            "kd": round(distance_pid["kd"], 4),
        },
    }

    with open(output_path, "w") as f:
        yaml.dump(results, f, default_flow_style=False)


def main():
    """Run PID tuning."""
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")

    print("Loading sensor data...")
    print(f"Loaded {len(sensor_data)} data points")

    speed_pid, distance_pid = grid_search_tuning(config, sensor_data)

    # Save tuning results
    save_tuning_results(speed_pid, distance_pid, "/root/tuning_results.yaml")
    print(f"\nTuning results saved to tuning_results.yaml")
    print(f"Speed PID: {speed_pid}")
    print(f"Distance PID: {distance_pid}")


if __name__ == "__main__":
    main()

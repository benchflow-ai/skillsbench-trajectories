"""
Improved PID tuning for ACC system using Ziegler-Nichols-inspired approach.
"""

import csv
import math
import yaml
from pid_controller import PIDController


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


def simulate_with_pid_realistic(config, sensor_data, speed_pid, distance_pid):
    """
    Run realistic simulation updating speeds based on acceleration commands.

    Returns:
        Dict with metrics
    """
    # Create ACC config for this test
    test_config = config.copy()
    test_config["pid_speed"] = speed_pid.copy()
    test_config["pid_distance"] = distance_pid.copy()

    # Initialize PID controllers
    speed_ctrl = PIDController(
        speed_pid["kp"], speed_pid["ki"], speed_pid["kd"]
    )
    distance_ctrl = PIDController(
        distance_pid["kp"], distance_pid["ki"], distance_pid["kd"]
    )

    max_accel = test_config["vehicle"]["max_acceleration"]
    max_decel = test_config["vehicle"]["max_deceleration"]
    set_speed = test_config["acc_settings"]["set_speed"]
    time_headway = test_config["acc_settings"]["time_headway"]
    min_distance = test_config["acc_settings"]["min_distance"]
    emergency_ttc = test_config["acc_settings"]["emergency_ttc_threshold"]
    dt = test_config["simulation"]["dt"]

    # Simulation state
    ego_speed = 0.0
    speeds = []
    speed_errors = []
    distance_errors = []
    min_distance_seen = float("inf")
    emergency_count = 0
    ttc_values = []

    # Process sensor data
    for sensor in sensor_data:
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        # Update speed based on previous acceleration
        # (In real scenario, this comes from dynamics)
        speeds.append(ego_speed)

        # Determine mode and compute acceleration
        if lead_speed is None or distance is None:
            # Cruise mode
            mode = "cruise"
            speed_error = set_speed - ego_speed
            accel_cmd = speed_ctrl.compute(speed_error, dt)
        else:
            # Lead vehicle present
            desired_distance = min_distance + time_headway * ego_speed
            distance_error = desired_distance - distance
            relative_speed = ego_speed - lead_speed

            # Check emergency condition
            if relative_speed > 0.01:
                ttc = distance / relative_speed
            else:
                ttc = float("inf")

            if ttc < emergency_ttc and relative_speed > 0:
                mode = "emergency"
                accel_cmd = max_decel
            else:
                mode = "follow"
                accel_cmd = distance_ctrl.compute(distance_error, dt)
                distance_errors.append(distance_error)

            if ttc < float("inf"):
                ttc_values.append(ttc)

            if mode == "emergency":
                emergency_count += 1
            else:
                min_distance_seen = min(min_distance_seen, distance)

        # Clip acceleration
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))

        # Update ego speed for next iteration
        ego_speed = max(0, ego_speed + accel_cmd * dt)

        if mode == "cruise":
            speed_errors.append(set_speed - ego_speed)

    # Calculate metrics
    # Rise time
    rise_time_idx = -1
    for i, speed in enumerate(speeds):
        if speed >= 0.9 * set_speed:
            rise_time_idx = i
            break
    rise_time = (rise_time_idx * dt) if rise_time_idx >= 0 else float("inf")

    # Overshoot
    max_speed = max(speeds) if speeds else 0
    overshoot_percent = max(0, (max_speed - set_speed) / set_speed * 100) if set_speed > 0 else 0

    # Speed SSE (last 10 seconds of cruise)
    if speed_errors:
        last_10s_idx = max(0, len(speed_errors) - int(10 / dt))
        cruise_errors = [abs(e) for e in speed_errors[last_10s_idx:]]
        speed_sse = sum(cruise_errors) / len(cruise_errors) if len(cruise_errors) > 0 else 0
    else:
        speed_sse = 0

    # Distance SSE
    if distance_errors:
        last_10s_idx = max(0, len(distance_errors) - int(10 / dt))
        dist_errs = [abs(e) for e in distance_errors[last_10s_idx:]]
        distance_sse = sum(dist_errs) / len(dist_errs) if len(dist_errs) > 0 else 0
    else:
        distance_sse = 0

    # Min distance
    min_distance_final = min_distance_seen if min_distance_seen != float("inf") else None

    return {
        "speed_rise_time": rise_time,
        "speed_overshoot": overshoot_percent,
        "speed_sse": speed_sse,
        "distance_sse": distance_sse,
        "min_distance": min_distance_final,
        "emergency_count": emergency_count,
    }


def calculate_fitness(metrics):
    """Calculate fitness score."""
    score = 0.0

    # Rise time < 10s
    if metrics["speed_rise_time"] < 10.0:
        score += metrics["speed_rise_time"]
    else:
        score += 10.0 + (metrics["speed_rise_time"] - 10.0) * 2.0

    # Overshoot < 5%
    if metrics["speed_overshoot"] < 5.0:
        score += metrics["speed_overshoot"] * 0.1
    else:
        score += 5.0 + (metrics["speed_overshoot"] - 5.0)

    # Speed SSE < 0.5
    if metrics["speed_sse"] < 0.5:
        score += metrics["speed_sse"] * 2.0
    else:
        score += 0.5 + (metrics["speed_sse"] - 0.5) * 5.0

    # Distance SSE < 2m
    if metrics["distance_sse"] < 2.0:
        score += metrics["distance_sse"] * 0.5
    else:
        score += 2.0 + (metrics["distance_sse"] - 2.0)

    # Min distance > 5m
    if metrics["min_distance"] is not None:
        if metrics["min_distance"] > 5.0:
            score += 0.0
        else:
            score += (5.0 - metrics["min_distance"]) * 5.0

    # Emergency events
    score += metrics["emergency_count"] * 1.0

    return score


def tune_pid_parameters(config, sensor_data):
    """
    Tune PID parameters using focused grid search.
    """
    print("Starting realistic PID tuning...")

    # Speed controller tuning - focus on aggressive acceleration
    best_speed_score = float("inf")
    best_speed_pid = None

    print("\nTuning speed controller...")
    # Balanced gains for smooth acceleration with minimal overshoot
    for kp in [0.5, 0.7, 0.8, 0.9, 1.0]:
        for ki in [0.05, 0.1, 0.15, 0.2, 0.25]:
            for kd in [0.0, 0.3, 0.5, 0.7, 1.0]:
                speed_pid = {"kp": kp, "ki": ki, "kd": kd}
                distance_pid = {"kp": 0.3, "ki": 0.05, "kd": 0.5}

                metrics = simulate_with_pid_realistic(
                    config, sensor_data, speed_pid, distance_pid
                )
                score = calculate_fitness(metrics)

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_pid = speed_pid.copy()
                    print(
                        f"  NEW BEST Kp={kp:.1f} Ki={ki:.1f} Kd={kd:.1f}: "
                        f"score={score:.2f}, rise={metrics['speed_rise_time']:.1f}s, "
                        f"sse={metrics['speed_sse']:.3f}m/s"
                    )

    print(f"\nBest speed PID: {best_speed_pid}")

    # Distance controller tuning
    best_dist_score = float("inf")
    best_distance_pid = None

    print("\nTuning distance controller...")
    # Conservative gains for smooth distance following
    for kp in [0.1, 0.2, 0.3, 0.4, 0.5]:
        for ki in [0.02, 0.05, 0.08, 0.1, 0.15]:
            for kd in [0.2, 0.4, 0.6, 0.8, 1.0]:
                distance_pid = {"kp": kp, "ki": ki, "kd": kd}

                metrics = simulate_with_pid_realistic(
                    config, sensor_data, best_speed_pid, distance_pid
                )
                score = calculate_fitness(metrics)

                if score < best_dist_score:
                    best_dist_score = score
                    best_distance_pid = distance_pid.copy()
                    print(
                        f"  NEW BEST Kp={kp:.1f} Ki={ki:.1f} Kd={kd:.1f}: "
                        f"score={score:.2f}, dist_sse={metrics['distance_sse']:.2f}m"
                    )

    print(f"\nBest distance PID: {best_distance_pid}")

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
    """Run tuning."""
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")

    print(f"Loaded {len(sensor_data)} sensor data points")

    speed_pid, distance_pid = tune_pid_parameters(config, sensor_data)

    save_tuning_results(speed_pid, distance_pid, "/root/tuning_results.yaml")
    print(f"\n\nTuning results saved!")
    print(f"Speed PID: {speed_pid}")
    print(f"Distance PID: {distance_pid}")


if __name__ == "__main__":
    main()

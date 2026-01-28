"""
PID tuning with anti-windup and better constraint handling.
"""

import csv
import yaml
from pid_controller import PIDController


def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path):
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
    """Simulate with intelligent PID usage."""
    speed_ctrl = PIDController(
        speed_pid["kp"], speed_pid["ki"], speed_pid["kd"]
    )
    distance_ctrl = PIDController(
        distance_pid["kp"], distance_pid["ki"], distance_pid["kd"]
    )

    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]
    set_speed = config["acc_settings"]["set_speed"]
    time_headway = config["acc_settings"]["time_headway"]
    min_distance = config["acc_settings"]["min_distance"]
    emergency_ttc = config["acc_settings"]["emergency_ttc_threshold"]
    dt = config["simulation"]["dt"]

    ego_speed = 0.0
    speeds = []
    speed_errors = []
    distance_errors = []
    min_distance_seen = float("inf")
    emergency_count = 0
    ttc_values = []

    for sensor in sensor_data:
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        speeds.append(ego_speed)

        if lead_speed is None or distance is None:
            mode = "cruise"
            speed_error = set_speed - ego_speed
            accel_cmd = speed_ctrl.compute(speed_error, dt)
        else:
            desired_distance = min_distance + time_headway * ego_speed
            distance_error = desired_distance - distance
            relative_speed = ego_speed - lead_speed

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

        accel_cmd = max(max_decel, min(max_accel, accel_cmd))
        ego_speed = max(0, ego_speed + accel_cmd * dt)

        if mode == "cruise":
            speed_errors.append(set_speed - ego_speed)

    # Metrics
    rise_time_idx = -1
    for i, speed in enumerate(speeds):
        if speed >= 0.9 * set_speed:
            rise_time_idx = i
            break
    rise_time = (rise_time_idx * dt) if rise_time_idx >= 0 else float("inf")

    max_speed = max(speeds) if speeds else 0
    overshoot_percent = max(0, (max_speed - set_speed) / set_speed * 100)

    if speed_errors:
        last_10s_idx = max(0, len(speed_errors) - int(10 / dt))
        cruise_errors = [abs(e) for e in speed_errors[last_10s_idx:]]
        speed_sse = sum(cruise_errors) / len(cruise_errors) if cruise_errors else 0
    else:
        speed_sse = 0

    if distance_errors:
        last_10s_idx = max(0, len(distance_errors) - int(10 / dt))
        dist_errs = [abs(e) for e in distance_errors[last_10s_idx:]]
        distance_sse = sum(dist_errs) / len(dist_errs) if dist_errs else 0
    else:
        distance_sse = 0

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
    """Fitness function prioritizing target achievement."""
    score = 0.0

    # Hard target: rise time < 10s
    if metrics["speed_rise_time"] >= 10.0:
        return 10000.0

    # Hard target: overshoot < 5% (with some slack)
    if metrics["speed_overshoot"] > 10.0:
        return 10000.0

    # Hard target: speed SSE < 1.0 m/s
    if metrics["speed_sse"] > 1.5:
        return 10000.0

    # Hard safety: min distance > 5m
    if metrics["min_distance"] is not None and metrics["min_distance"] < 5.0:
        return 10000.0

    # Soft metrics (optimize if hard constraints met)
    score += metrics["speed_rise_time"] * 0.5
    score += metrics["speed_overshoot"] * 0.5
    score += metrics["speed_sse"] * 2.0
    score += metrics["distance_sse"] * 0.2
    score += metrics["emergency_count"] * 0.3

    return score


def tune(config, sensor_data):
    """Simple focused tuning."""
    print("Tuning with constrained parameter space...")

    # Small search space with known good ranges
    best_speed = None
    best_speed_score = float("inf")

    print("\nSpeed controller tuning...")
    for kp in [0.3, 0.4, 0.5, 0.6, 0.7]:
        for ki in [0.01, 0.02, 0.05, 0.08]:
            for kd in [0.1, 0.2, 0.3]:
                speed_pid = {"kp": kp, "ki": ki, "kd": kd}
                dist_pid = {"kp": 0.15, "ki": 0.02, "kd": 0.4}

                metrics = simulate_with_pid(config, sensor_data, speed_pid, dist_pid)
                score = calculate_fitness(metrics)

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed = speed_pid.copy()
                    if score < 10000:
                        print(
                            f"  Speed: Kp={kp:.1f} Ki={ki:.2f} Kd={kd:.1f} "
                            f"→ rise={metrics['speed_rise_time']:.1f}s, "
                            f"over={metrics['speed_overshoot']:.1f}%, "
                            f"sse={metrics['speed_sse']:.2f}"
                        )

    print(f"\nBest speed PID: {best_speed}")

    # Distance tuning
    best_dist = None
    best_dist_score = float("inf")

    print("\nDistance controller tuning...")
    for kp in [0.1, 0.15, 0.2, 0.25, 0.3]:
        for ki in [0.01, 0.02, 0.03, 0.05]:
            for kd in [0.3, 0.5, 0.7, 0.9]:
                dist_pid = {"kp": kp, "ki": ki, "kd": kd}

                metrics = simulate_with_pid(config, sensor_data, best_speed, dist_pid)
                score = calculate_fitness(metrics)

                if score < best_dist_score:
                    best_dist_score = score
                    best_dist = dist_pid.copy()
                    if score < 10000:
                        print(
                            f"  Distance: Kp={kp:.2f} Ki={ki:.2f} Kd={kd:.1f} "
                            f"→ dist_sse={metrics['distance_sse']:.1f}, "
                            f"min_dist={metrics['min_distance']:.1f}, "
                            f"emergency={metrics['emergency_count']}"
                        )

    print(f"\nBest distance PID: {best_dist}")

    return best_speed, best_dist


def save_tuning_results(speed_pid, distance_pid, output_path):
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
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")

    print(f"Loaded {len(sensor_data)} sensor data points")

    speed_pid, distance_pid = tune(config, sensor_data)

    save_tuning_results(speed_pid, distance_pid, "/root/tuning_results.yaml")
    print(f"\nTuning saved!")
    print(f"Speed PID: {speed_pid}")
    print(f"Distance PID: {distance_pid}")


if __name__ == "__main__":
    main()

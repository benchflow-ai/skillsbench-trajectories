"""Final PID Parameter Tuner with improved distance control focus."""

import csv
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


def simulate_with_gains(config, sensor_data, kp_speed, ki_speed, kd_speed,
                        kp_dist, ki_dist, kd_dist):
    """Run simulation with given PID gains."""
    test_config = dict(config)
    test_config["pid_speed"] = {"kp": kp_speed, "ki": ki_speed, "kd": kd_speed}
    test_config["pid_distance"] = {"kp": kp_dist, "ki": ki_dist, "kd": kd_dist}

    acc = AdaptiveCruiseControl(test_config)
    dt = config["simulation"]["dt"]
    set_speed = config["acc_settings"]["set_speed"]
    min_distance = config["acc_settings"]["min_distance"]
    time_headway = config["acc_settings"]["time_headway"]

    current_speed = 0.0
    cruise_speeds = []
    cruise_times = []
    distance_errors = []
    actual_distances = []
    follow_count = 0
    rise_time = None
    max_speed = 0.0

    for data_point in sensor_data:
        time = data_point["time"]
        lead_speed = data_point["lead_speed"]
        distance = data_point["distance"]

        accel_cmd, mode, dist_error = acc.compute(
            current_speed, lead_speed, distance, dt
        )

        new_speed = current_speed + accel_cmd * dt
        new_speed = max(0.0, new_speed)
        current_speed = new_speed

        if lead_speed is None:
            cruise_speeds.append(current_speed)
            cruise_times.append(time)
            max_speed = max(max_speed, current_speed)

            if rise_time is None and current_speed >= 0.9 * set_speed:
                rise_time = time

        if dist_error is not None:
            distance_errors.append(abs(dist_error))
            follow_count += 1

        if distance is not None:
            actual_distances.append(distance)

    metrics = {}

    # Cruise metrics
    metrics["rise_time"] = rise_time if rise_time is not None else 150.0
    metrics["overshoot"] = max(0, (max_speed - set_speed) / set_speed * 100)

    if cruise_speeds:
        ss_end = min(30.0, cruise_times[-1])
        ss_indices = [i for i, t in enumerate(cruise_times) if t >= ss_end - 10.0]
        if ss_indices:
            ss_speeds = [cruise_speeds[i] for i in ss_indices]
            metrics["speed_sse"] = (
                sum(abs(set_speed - s) for s in ss_speeds) / len(ss_speeds)
            )
        else:
            metrics["speed_sse"] = abs(set_speed - cruise_speeds[-1])
    else:
        metrics["speed_sse"] = 100.0

    # Follow metrics
    if distance_errors:
        # Exclude outliers in early follow phase
        sorted_errors = sorted(distance_errors)
        # Use 25-75 percentile for more robust estimate
        q1_idx = len(sorted_errors) // 4
        q3_idx = 3 * len(sorted_errors) // 4
        if q3_idx > q1_idx:
            robust_errors = sorted_errors[q1_idx:q3_idx]
            metrics["distance_mse"] = sum(robust_errors) / len(robust_errors)
        else:
            metrics["distance_mse"] = sum(distance_errors) / len(distance_errors)
    else:
        metrics["distance_mse"] = 100.0

    # Safety metric
    metrics["min_distance"] = min(actual_distances) if actual_distances else 0.0

    # Weighted scoring
    score = 0

    # Rise time (must be < 10s, weight: 20)
    rt_penalty = max(0, (metrics["rise_time"] - 10) / 10) * 20
    score += rt_penalty

    # Overshoot (must be < 5%, weight: 10)
    os_penalty = max(0, (metrics["overshoot"] - 5) / 5) * 10
    score += os_penalty

    # Speed error (must be < 0.5 m/s, weight: 20)
    if metrics["speed_sse"] > 0.5:
        speed_penalty = (metrics["speed_sse"] - 0.5) * 20
    else:
        speed_penalty = 0
    score += speed_penalty

    # Distance error (must be < 2m, weight: 30)
    if metrics["distance_mse"] > 2.0:
        dist_penalty = (metrics["distance_mse"] - 2.0) * 15
    else:
        dist_penalty = 0
    score += dist_penalty

    # Min distance safety (must be > 5m, weight: 50)
    if metrics["min_distance"] < 5.0:
        safe_penalty = (5.0 - metrics["min_distance"]) * 50
    else:
        safe_penalty = 0
    score += safe_penalty

    metrics["score"] = score

    return metrics


def tune_final(config_path, sensor_data_path):
    """Comprehensive tuning."""
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_data_path)

    # Use known good speed controller
    best_speed = {"kp": 5.0, "ki": 0.1, "kd": 3.0}

    # Extensive distance controller search
    print("Tuning distance controller with focus on safety and distance accuracy...\n")

    best_score = float("inf")
    best_dist = {"kp": 0.5, "ki": 0.05, "kd": 0.0}

    # Wider search ranges for distance controller
    kp_dist_range = [0.2, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    ki_dist_range = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
    kd_dist_range = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]

    tested = 0
    for kp in kp_dist_range:
        for ki in ki_dist_range:
            for kd in kd_dist_range:
                result = simulate_with_gains(
                    config,
                    sensor_data,
                    best_speed["kp"],
                    best_speed["ki"],
                    best_speed["kd"],
                    kp,
                    ki,
                    kd,
                )
                tested += 1

                if result["score"] < best_score:
                    best_score = result["score"]
                    best_dist = {"kp": kp, "ki": ki, "kd": kd}

                    print(
                        f"[{tested}] Score: {result['score']:7.2f} | "
                        f"MinDist: {result['min_distance']:5.2f}m | "
                        f"DistErr: {result['distance_mse']:6.2f}m | "
                        f"kp={kp:5.2f} ki={ki:5.2f} kd={kd:5.2f}"
                    )

    print(f"\nTested {tested} configurations")

    return best_speed, best_dist


def main():
    """Run tuning and save results."""
    config_path = "/root/vehicle_params.yaml"
    sensor_data_path = "/root/sensor_data.csv"

    print("Starting final PID tuning...\n")
    best_speed, best_dist = tune_final(config_path, sensor_data_path)

    output = {
        "pid_speed": best_speed,
        "pid_distance": best_dist,
    }

    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(output, f, default_flow_style=False)

    print("\n\nFinal tuning complete.")
    print(f"\nSpeed controller: kp={best_speed['kp']}, ki={best_speed['ki']}, kd={best_speed['kd']}")
    print(f"Distance controller: kp={best_dist['kp']}, ki={best_dist['ki']}, kd={best_dist['kd']}")


if __name__ == "__main__":
    main()

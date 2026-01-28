"""Optimized PID Parameter Tuner for ACC System targeting specific metrics."""

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


def compute_ttc(ego_speed, lead_speed, distance):
    """Compute time-to-collision."""
    if lead_speed is None or distance is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None

    if distance <= 0:
        return 0.0

    return distance / relative_speed


def simulate_with_gains(config, sensor_data, kp_speed, ki_speed, kd_speed,
                        kp_dist, ki_dist, kd_dist):
    """Run simulation with given PID gains and compute comprehensive metrics."""
    # Create a copy of config with new gains
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

        # Track cruise phase (no lead vehicle)
        if lead_speed is None:
            cruise_speeds.append(current_speed)
            cruise_times.append(time)
            max_speed = max(max_speed, current_speed)

            # Detect 90% rise time
            if rise_time is None and current_speed >= 0.9 * set_speed:
                rise_time = time

        # Track follow phase errors
        if dist_error is not None:
            distance_errors.append(abs(dist_error))

        if distance is not None:
            actual_distances.append(distance)

    # Calculate metrics
    metrics = {}

    # Rise time (target < 10s)
    metrics["rise_time"] = rise_time if rise_time is not None else 150.0

    # Overshoot (target < 5%)
    metrics["overshoot"] = max(0, (max_speed - set_speed) / set_speed * 100)

    # Speed steady-state error (target < 0.5 m/s)
    if cruise_speeds:
        # Last 10 seconds of cruise
        ss_end = min(30.0, cruise_times[-1])  # Use last 10s or available time
        ss_indices = [
            i
            for i, t in enumerate(cruise_times)
            if t >= ss_end - 10.0
        ]
        if ss_indices:
            ss_speeds = [cruise_speeds[i] for i in ss_indices]
            metrics["speed_sse"] = (
                sum(abs(set_speed - s) for s in ss_speeds) / len(ss_speeds)
            )
        else:
            metrics["speed_sse"] = abs(set_speed - cruise_speeds[-1])
    else:
        metrics["speed_sse"] = 100.0

    # Distance error (target < 2m)
    metrics["distance_mse"] = (
        sum(distance_errors) / len(distance_errors) if distance_errors else 100.0
    )

    # Minimum distance (target > 5m)
    metrics["min_distance"] = min(actual_distances) if actual_distances else 0.0

    # Scoring function tailored to targets
    score = 0

    # Rise time penalty (target < 10s)
    rt_penalty = max(0, (metrics["rise_time"] - 10) / 10) * 40
    score += rt_penalty

    # Overshoot penalty (target < 5%)
    os_penalty = max(0, (metrics["overshoot"] - 5) / 5) * 30
    score += os_penalty

    # Speed error penalty (target < 0.5 m/s)
    speed_penalty = (metrics["speed_sse"] / 0.5) * 20 if metrics["speed_sse"] > 0.5 else 0
    score += speed_penalty

    # Distance error penalty (target < 2m)
    dist_penalty = (metrics["distance_mse"] / 2.0) * 15 if metrics["distance_mse"] > 2.0 else 0
    score += dist_penalty

    # Min distance penalty (target > 5m)
    min_dist_penalty = max(0, (5.0 - metrics["min_distance"]) / 5.0) * 25
    score += min_dist_penalty

    metrics["score"] = score

    return metrics


def tune_pids(config_path, sensor_data_path):
    """
    Tune PID parameters using optimized grid search.

    Returns:
        Best gains as dict
    """
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_data_path)

    # Refined grid search ranges
    kp_range = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]
    ki_range = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
    kd_range = [0.0, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0]

    best_score = float("inf")
    best_gains = {
        "pid_speed": {"kp": 0.5, "ki": 0.05, "kd": 0.5},
        "pid_distance": {"kp": 0.5, "ki": 0.05, "kd": 0.0},
    }

    print("Tuning speed controller (cruise phase)...")
    for kp in kp_range:
        for ki in ki_range:
            for kd in kd_range:
                result = simulate_with_gains(
                    config, sensor_data, kp, ki, kd, 0.5, 0.05, 0.0
                )

                # Focus on rise time and overshoot for speed control
                if (
                    result["rise_time"] < 12
                    and result["overshoot"] < 10
                ):
                    if result["score"] < best_score:
                        best_score = result["score"]
                        best_gains["pid_speed"] = {"kp": kp, "ki": ki, "kd": kd}
                        print(
                            f"  New best score: {result['score']:.2f} | "
                            f"Rise time: {result['rise_time']:.2f}s, "
                            f"Overshoot: {result['overshoot']:.2f}%, "
                            f"Speed SSE: {result['speed_sse']:.3f}"
                        )

    # Tune distance controller
    print("\nTuning distance controller (follow phase)...")
    best_dist_score = float("inf")
    kp_dist_range = [0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0]
    ki_dist_range = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5]
    kd_dist_range = [0.0, 0.1, 0.2, 0.5, 1.0]

    for kp in kp_dist_range:
        for ki in ki_dist_range:
            for kd in kd_dist_range:
                result = simulate_with_gains(
                    config,
                    sensor_data,
                    best_gains["pid_speed"]["kp"],
                    best_gains["pid_speed"]["ki"],
                    best_gains["pid_speed"]["kd"],
                    kp,
                    ki,
                    kd,
                )

                # Focus on distance control and safety
                if (
                    result["min_distance"] > 4.0
                    and result["distance_mse"] < 20.0
                ):
                    if result["score"] < best_dist_score:
                        best_dist_score = result["score"]
                        best_gains["pid_distance"] = {"kp": kp, "ki": ki, "kd": kd}
                        print(
                            f"  New best score: {result['score']:.2f} | "
                            f"Min dist: {result['min_distance']:.2f}m, "
                            f"Distance MSE: {result['distance_mse']:.2f}m"
                        )

    return best_gains


def main():
    """Run tuning and save results."""
    config_path = "/root/vehicle_params.yaml"
    sensor_data_path = "/root/sensor_data.csv"

    print("Starting optimized PID tuning...\n")
    best_gains = tune_pids(config_path, sensor_data_path)

    # Save results
    output = {
        "pid_speed": best_gains["pid_speed"],
        "pid_distance": best_gains["pid_distance"],
    }

    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(output, f, default_flow_style=False)

    print("\n\nTuning complete. Results saved to /root/tuning_results.yaml")
    print("\nBest gains found:")
    print(f"Speed controller:")
    print(f"  kp={output['pid_speed']['kp']}, ki={output['pid_speed']['ki']}, kd={output['pid_speed']['kd']}")
    print(f"Distance controller:")
    print(f"  kp={output['pid_distance']['kp']}, ki={output['pid_distance']['ki']}, kd={output['pid_distance']['kd']}")


if __name__ == "__main__":
    main()

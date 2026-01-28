"""PID Parameter Tuner for ACC System."""

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
    """Run simulation with given PID gains."""
    # Create a copy of config with new gains
    test_config = dict(config)
    test_config["pid_speed"] = {"kp": kp_speed, "ki": ki_speed, "kd": kd_speed}
    test_config["pid_distance"] = {"kp": kp_dist, "ki": ki_dist, "kd": kd_dist}

    acc = AdaptiveCruiseControl(test_config)
    dt = config["simulation"]["dt"]
    set_speed = config["acc_settings"]["set_speed"]

    current_speed = 0.0
    speed_errors = []
    distance_errors = []
    rise_time_reached = False
    rise_time = None
    max_speed = 0.0

    for data_point in sensor_data:
        lead_speed = data_point["lead_speed"]
        distance = data_point["distance"]

        accel_cmd, mode, dist_error = acc.compute(
            current_speed, lead_speed, distance, dt
        )

        new_speed = current_speed + accel_cmd * dt
        new_speed = max(0.0, new_speed)
        current_speed = new_speed

        # Track metrics for cruise phase (no lead vehicle)
        if lead_speed is None:
            speed_errors.append(set_speed - current_speed)
            max_speed = max(max_speed, current_speed)

            # Detect 90% rise time (only once)
            if (
                not rise_time_reached
                and current_speed >= 0.9 * set_speed
                and rise_time is None
            ):
                rise_time = data_point["time"]
                rise_time_reached = True

        # Track distance errors for follow phase
        if dist_error is not None:
            distance_errors.append(abs(dist_error))

    # Calculate metrics
    cruise_phase_end = 150  # End of cruise phase before lead vehicle
    final_speed_error = abs(speed_errors[-1]) if speed_errors else 0
    mean_distance_error = (
        sum(distance_errors) / len(distance_errors) if distance_errors else 0
    )
    overshoot = (
        ((max_speed - set_speed) / set_speed * 100) if max_speed > set_speed else 0
    )
    rise_time = rise_time if rise_time is not None else 150

    # Scoring function (lower is better)
    # Weighted metrics
    score = 0
    score += (max(0, rise_time - 10) / 10) * 20  # Rise time penalty (weight: 20)
    score += min(overshoot, 10) * 5  # Overshoot penalty (weight: 5)
    score += final_speed_error * 100  # Speed error penalty (weight: 100)
    score += mean_distance_error * 50  # Distance error penalty (weight: 50)

    return {
        "score": score,
        "rise_time": rise_time,
        "overshoot": overshoot,
        "speed_sse": final_speed_error,
        "distance_mse": mean_distance_error,
    }


def tune_pids(config_path, sensor_data_path):
    """
    Tune PID parameters using grid search.

    Returns:
        Best gains as dict
    """
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_data_path)

    # Grid search ranges
    kp_range = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    ki_range = [0.01, 0.05, 0.1, 0.2, 0.3, 0.5]
    kd_range = [0.0, 0.5, 1.0, 2.0, 3.0]

    best_score = float("inf")
    best_gains = None

    # Tune speed controller first
    print("Tuning speed controller...")
    for kp in kp_range:
        for ki in ki_range:
            for kd in kd_range:
                result = simulate_with_gains(
                    config, sensor_data, kp, ki, kd, 0.1, 0.01, 0.0
                )
                if result["score"] < best_score:
                    best_score = result["score"]
                    best_gains = {
                        "pid_speed": {"kp": kp, "ki": ki, "kd": kd},
                        "pid_distance": {"kp": 0.1, "ki": 0.01, "kd": 0.0},
                    }
                    print(f"  Speed controller - Score: {result['score']:.2f}")
                    print(f"    kp={kp}, ki={ki}, kd={kd}")

    # Tune distance controller with best speed controller
    print("\nTuning distance controller...")
    best_dist_score = float("inf")
    best_dist_gains = None

    for kp in kp_range:
        for ki in ki_range:
            for kd in kd_range:
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
                if result["score"] < best_dist_score:
                    best_dist_score = result["score"]
                    best_dist_gains = {
                        "pid_speed": best_gains["pid_speed"],
                        "pid_distance": {"kp": kp, "ki": ki, "kd": kd},
                    }
                    print(f"  Distance controller - Score: {result['score']:.2f}")
                    print(f"    kp={kp}, ki={ki}, kd={kd}")

    return best_dist_gains


def main():
    """Run tuning and save results."""
    config_path = "/root/vehicle_params.yaml"
    sensor_data_path = "/root/sensor_data.csv"

    print("Starting PID tuning...")
    best_gains = tune_pids(config_path, sensor_data_path)

    # Save results
    output = {
        "pid_speed": best_gains["pid_speed"],
        "pid_distance": best_gains["pid_distance"],
    }

    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(output, f, default_flow_style=False)

    print("\nTuning complete. Results saved to /root/tuning_results.yaml")
    print("\nBest gains found:")
    print(f"Speed controller: kp={output['pid_speed']['kp']}, "
          f"ki={output['pid_speed']['ki']}, kd={output['pid_speed']['kd']}")
    print(f"Distance controller: kp={output['pid_distance']['kp']}, "
          f"ki={output['pid_distance']['ki']}, kd={output['pid_distance']['kd']}")


if __name__ == "__main__":
    main()

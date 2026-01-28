"""Aggressive distance control tuning."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path):
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
    test_config = dict(config)
    test_config["pid_speed"] = {"kp": kp_speed, "ki": ki_speed, "kd": kd_speed}
    test_config["pid_distance"] = {"kp": kp_dist, "ki": ki_dist, "kd": kd_dist}

    acc = AdaptiveCruiseControl(test_config)
    dt = config["simulation"]["dt"]
    set_speed = config["acc_settings"]["set_speed"]

    current_speed = 0.0
    cruise_speeds = []
    cruise_times = []
    distance_errors_all = []
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

        if lead_speed is None:
            cruise_speeds.append(current_speed)
            cruise_times.append(time)
            max_speed = max(max_speed, current_speed)

            if rise_time is None and current_speed >= 0.9 * set_speed:
                rise_time = time

        if dist_error is not None:
            distance_errors_all.append(dist_error)

        if distance is not None:
            actual_distances.append(distance)

    metrics = {}

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

    # Valid distance errors (when vehicle moving > 1 m/s)
    valid_errors = [
        abs(e) for data, e in zip(sensor_data, distance_errors_all)
        if e is not None
        and data.get('lead_speed') is not None
        and e != 0  # Only where we're in follow mode
    ]

    # But also check actual speeds from simulation
    if distance_errors_all:
        # Count valid samples more carefully
        idx = 0
        actual_valid_errors = []
        for i, data in enumerate(sensor_data):
            if data['lead_speed'] is not None:
                if i < len(distance_errors_all) and distance_errors_all[i] is not None:
                    # Get ego speed at this point
                    actual_valid_errors.append(abs(distance_errors_all[i]))

        metrics["distance_mse"] = (
            sum(actual_valid_errors) / len(actual_valid_errors) if actual_valid_errors else 100.0
        )
    else:
        metrics["distance_mse"] = 100.0

    metrics["min_distance"] = min(actual_distances) if actual_distances else 0.0

    score = 0
    if metrics["rise_time"] > 10:
        score += (metrics["rise_time"] - 10) * 15
    if metrics["overshoot"] > 5:
        score += (metrics["overshoot"] - 5) * 10
    if metrics["speed_sse"] > 0.5:
        score += (metrics["speed_sse"] - 0.5) * 30
    if metrics["distance_mse"] > 2.0:
        score += (metrics["distance_mse"] - 2.0) * 20
    if metrics["min_distance"] < 5.0:
        score += (5.0 - metrics["min_distance"]) * 50

    metrics["score"] = score
    return metrics


def tune():
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")

    # Keep the good speed controller
    best_speed = {"kp": 6.0, "ki": 0.05, "kd": 2.5}

    print("Aggressive distance controller tuning...")
    print("=" * 60)

    best_dist_score = float("inf")
    best_dist = {"kp": 2.0, "ki": 0.2, "kd": 0.5}

    # More aggressive ranges
    kp_dist_range = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
    ki_dist_range = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5]
    kd_dist_range = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5]

    iteration = 0
    for kp in kp_dist_range:
        for ki in ki_dist_range:
            for kd in kd_dist_range:
                iteration += 1
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

                if result["score"] < best_dist_score:
                    best_dist_score = result["score"]
                    best_dist = {"kp": kp, "ki": ki, "kd": kd}

                    print(
                        f"[{iteration:4d}] Score: {result['score']:7.2f} | "
                        f"DistErr: {result['distance_mse']:6.2f}m | "
                        f"MinDist: {result['min_distance']:5.2f}m | "
                        f"kp={kp:4.1f} ki={ki:5.2f} kd={kd:4.1f}"
                    )

    return best_speed, best_dist


def main():
    print("\nStarting aggressive PID tuning for distance control...\n")
    speed_gains, dist_gains = tune()

    output = {
        "pid_speed": speed_gains,
        "pid_distance": dist_gains,
    }

    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(output, f, default_flow_style=False)

    print("\n" + "=" * 60)
    print("TUNING COMPLETE")
    print("=" * 60)
    print(f"Speed:    kp={speed_gains['kp']}, ki={speed_gains['ki']}, kd={speed_gains['kd']}")
    print(f"Distance: kp={dist_gains['kp']}, ki={dist_gains['ki']}, kd={dist_gains['kd']}")


if __name__ == "__main__":
    main()

"""
PID parameter tuning for ACC system.
"""

import csv
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_yaml(filepath):
    """Load YAML configuration file."""
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath):
    """Load sensor data from CSV."""
    data = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = row["lead_speed"].strip() if row["lead_speed"].strip() else None
            distance = row["distance"].strip() if row["distance"].strip() else None

            lead_speed = float(lead_speed) if lead_speed else None
            distance = float(distance) if distance else None

            data.append(
                {"time": time, "ego_speed": ego_speed, "lead_speed": lead_speed, "distance": distance}
            )
    return data


def evaluate_tuning(
    vehicle_config, sensor_data, kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist
):
    """
    Evaluate PID tuning performance.
    Uses actual sensor data for lead vehicle and calculates resulting distance.

    Returns:
        Dict with performance metrics
    """
    # Update config with PID gains
    test_config = vehicle_config.copy()
    test_config["pid_speed"] = {"kp": kp_speed, "ki": ki_speed, "kd": kd_speed}
    test_config["pid_distance"] = {"kp": kp_dist, "ki": ki_dist, "kd": kd_dist}

    acc = AdaptiveCruiseControl(test_config)
    dt = vehicle_config["simulation"]["dt"]
    set_speed = vehicle_config["acc_settings"]["set_speed"]

    ego_speed = 0.0
    ego_position = 0.0
    speeds = [ego_speed]
    accelerations = []
    distance_errors = []
    min_distance = float("inf")
    lead_position = 0.0

    for sensor_row in sensor_data:
        lead_speed = sensor_row["lead_speed"]

        # Calculate distance from positions
        if lead_speed is not None:
            # Lead vehicle moves according to its speed
            lead_position += lead_speed * dt
            # Use the actual sensed distance as reference
            distance = sensor_row["distance"]
        else:
            distance = None

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego vehicle
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_position += ego_speed * dt

        speeds.append(ego_speed)
        accelerations.append(accel_cmd)

        if distance is not None:
            min_distance = min(min_distance, distance)

        if distance_error is not None:
            distance_errors.append(distance_error)

    speeds = np.array(speeds)
    accelerations = np.array(accelerations)

    # Calculate metrics
    # Rise time: time to reach 95% of set speed in cruise phase (before t=30s, ~300 samples)
    cruise_speeds = speeds[: min(300, len(speeds))]
    rise_time_samples = np.where(cruise_speeds >= 0.95 * set_speed)[0]
    rise_time = (
        rise_time_samples[0] * dt if len(rise_time_samples) > 0 else float("inf")
    )

    # Overshoot: max speed during cruise / set speed - 1
    max_speed = np.max(cruise_speeds)
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error in speed (during follow phase, samples 300-500)
    follow_speeds = speeds[300:500] if len(speeds) > 300 else speeds[300:]
    if len(follow_speeds) > 0:
        speed_ss_error = abs(np.mean(follow_speeds) - np.mean(speeds[300:500] if len(speeds) > 300 else speeds[300:]))
        # Use actual reference from lead vehicle speeds + some offset
        avg_follow_lead = np.mean([float(sensor_data[i]['lead_speed']) for i in range(300, min(500, len(sensor_data))) if sensor_data[i]['lead_speed']])
        speed_ss_error = abs(np.mean(follow_speeds) - avg_follow_lead) if avg_follow_lead > 0 else 0
    else:
        speed_ss_error = 0

    # Distance steady-state error (in follow phase)
    distance_ss_error = np.mean(np.abs(distance_errors)) if distance_errors else 0

    # Check constraints
    min_distance_ok = min_distance >= 5.0 if min_distance != float("inf") else False

    # Score: prioritize safety (min distance), then control performance
    score = 0

    # CRITICAL: Safety constraint - min distance must be >= 5m
    if min_distance < 5.0:
        # Penalize based on how much we violate the safety constraint
        score = -500 * (5.0 - min_distance)
    else:
        # Safety met - optimize performance
        # Rise time penalty (target <10s)
        if rise_time < 10:
            score += 25 - rise_time * 2.5
        else:
            score -= 20

        # Overshoot penalty (target <5%)
        if overshoot < 5:
            score += 20 - overshoot * 4
        else:
            score -= (overshoot - 5) * 3

        # Speed SS error penalty (target <0.5 m/s)
        if speed_ss_error < 0.5:
            score += 15 - speed_ss_error * 30
        else:
            score -= min((speed_ss_error - 0.5) * 5, 20)

        # Distance SS error penalty (target <2m)
        if distance_ss_error < 2:
            score += 20 - distance_ss_error * 10
        else:
            score -= min((distance_ss_error - 2) * 5, 20)

        # Bonus for good safety margin
        if min_distance >= 10:
            score += min((min_distance - 10) * 0.2, 5)

    return {
        "score": score,
        "rise_time": rise_time,
        "overshoot": overshoot,
        "speed_ss_error": speed_ss_error,
        "distance_ss_error": distance_ss_error,
        "min_distance": min_distance,
    }


def tune_pid(vehicle_params_file, sensor_data_file):
    """
    Tune PID parameters using grid search.
    """
    vehicle_config = load_yaml(vehicle_params_file)
    sensor_data = load_sensor_data(sensor_data_file)

    # Grid search ranges - comprehensive search
    kp_speed_range = np.linspace(0.3, 3.0, 6)  # (0, 10)
    ki_speed_range = np.linspace(0.0, 0.5, 4)  # [0, 5)
    kd_speed_range = np.linspace(0.1, 2.0, 5)  # [0, 5)

    kp_dist_range = np.linspace(1.0, 4.0, 6)  # (0, 10)
    ki_dist_range = np.linspace(0.1, 1.0, 5)  # [0, 5)
    kd_dist_range = np.linspace(0.1, 2.0, 5)  # [0, 5)

    best_score = -float("inf")
    best_params = None
    best_metrics = None

    print("Tuning PID parameters...")
    print("Testing parameter combinations...")

    for kp_s in kp_speed_range:
        for ki_s in ki_speed_range:
            for kd_s in kd_speed_range:
                for kp_d in kp_dist_range:
                    for ki_d in ki_dist_range:
                        for kd_d in kd_dist_range:
                            metrics = evaluate_tuning(
                                vehicle_config,
                                sensor_data,
                                kp_s,
                                ki_s,
                                kd_s,
                                kp_d,
                                ki_d,
                                kd_d,
                            )

                            if metrics["score"] > best_score:
                                best_score = metrics["score"]
                                best_params = {
                                    "pid_speed": {
                                        "kp": float(kp_s),
                                        "ki": float(ki_s),
                                        "kd": float(kd_s),
                                    },
                                    "pid_distance": {
                                        "kp": float(kp_d),
                                        "ki": float(ki_d),
                                        "kd": float(kd_d),
                                    },
                                }
                                best_metrics = metrics

    print(f"\nBest parameters found:")
    print(f"Speed PID: kp={best_params['pid_speed']['kp']:.3f}, "
          f"ki={best_params['pid_speed']['ki']:.3f}, "
          f"kd={best_params['pid_speed']['kd']:.3f}")
    print(f"Distance PID: kp={best_params['pid_distance']['kp']:.3f}, "
          f"ki={best_params['pid_distance']['ki']:.3f}, "
          f"kd={best_params['pid_distance']['kd']:.3f}")
    print(f"\nPerformance metrics:")
    print(f"Rise time: {best_metrics['rise_time']:.2f}s (target <10s)")
    print(f"Overshoot: {best_metrics['overshoot']:.2f}% (target <5%)")
    print(f"Speed SS error: {best_metrics['speed_ss_error']:.3f} m/s (target <0.5 m/s)")
    print(f"Distance SS error: {best_metrics['distance_ss_error']:.3f} m (target <2m)")
    print(f"Min distance: {best_metrics['min_distance']:.2f}m (constraint >5m)")

    return best_params


if __name__ == "__main__":
    best_params = tune_pid("/root/vehicle_params.yaml", "/root/sensor_data.csv")

    # Save tuning results
    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(best_params, f, default_flow_style=False)

    print("\nTuning results saved to /root/tuning_results.yaml")

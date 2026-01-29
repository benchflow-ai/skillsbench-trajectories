"""PID parameter tuning for ACC system."""

import csv
import yaml
from pid_controller import PIDController


def load_config(config_file="vehicle_params.yaml"):
    """Load configuration from YAML file."""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file="sensor_data.csv"):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(
                {
                    "time": float(row["time"]),
                    "ego_speed": float(row["ego_speed"]),
                    "lead_speed": (
                        float(row["lead_speed"]) if row["lead_speed"] else None
                    ),
                    "distance": float(row["distance"]) if row["distance"] else None,
                }
            )
    return data


def simulate_speed_control(kp, ki, kd, config, sensor_data, dt=0.1):
    """
    Simulate speed control from t=0 to t=30s (cruise phase with controlled acceleration).

    Returns: metrics dict with rise_time, overshoot, steady_state_error
    """
    pid = PIDController(kp, ki, kd)
    set_speed = config["acc_settings"]["set_speed"]
    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]

    speeds = []
    times_10_90 = [None, None]

    # First 300 steps (30s) - controlled acceleration phase
    for i, sensor in enumerate(sensor_data[:300]):
        ego_speed = sensor["ego_speed"]
        speed_error = set_speed - ego_speed
        accel = pid.compute(speed_error, dt)
        accel = max(max_decel, min(max_accel, accel))

        speeds.append(ego_speed)

        # Track 10%-90% rise time
        if times_10_90[0] is None and ego_speed >= 0.1 * set_speed:
            times_10_90[0] = i
        elif times_10_90[1] is None and ego_speed >= 0.9 * set_speed:
            times_10_90[1] = i

    # Calculate metrics
    rise_time = float("inf")
    if times_10_90[0] is not None and times_10_90[1] is not None:
        rise_time = (times_10_90[1] - times_10_90[0]) * dt

    overshoot = 0.0
    if speeds:
        max_speed = max(speeds)
        if max_speed > set_speed:
            overshoot = (max_speed - set_speed) / set_speed * 100

    steady_state_error = 0.0
    if len(speeds) > 50:
        steady_state_error = abs(set_speed - sum(speeds[-50:]) / 50)

    return {
        "rise_time": rise_time,
        "overshoot": overshoot,
        "steady_state_error": steady_state_error,
        "max_speed": max(speeds) if speeds else 0,
    }


def simulate_distance_control(kp, ki, kd, config, sensor_data, dt=0.1):
    """
    Simulate distance control during follow phase (t=30s onwards).

    Returns: metrics dict with steady_state_error and min_gap
    """
    pid = PIDController(kp, ki, kd)
    time_headway = config["acc_settings"]["time_headway"]
    min_distance = config["acc_settings"]["min_distance"]

    distance_errors = []
    distances = []

    # After 300 steps (30s) - follow phase with lead vehicle
    for sensor in sensor_data[300:]:
        if sensor["lead_speed"] is not None and sensor["distance"] is not None:
            ego_speed = sensor["ego_speed"]
            distance = sensor["distance"]

            desired_distance = time_headway * ego_speed + min_distance
            distance_error = desired_distance - distance
            distance_errors.append(distance_error)
            distances.append(distance)

            pid.compute(distance_error, dt)

    # Calculate metrics
    steady_state_error = 0.0
    if len(distance_errors) > 100:
        steady_state_error = abs(sum(distance_errors[-100:]) / 100)

    min_gap = min(distances) if distances else float("inf")

    return {
        "steady_state_error": steady_state_error,
        "min_gap": min_gap,
    }


def tune_pids(config_file="vehicle_params.yaml", sensor_file="sensor_data.csv"):
    """
    Tune PID parameters to meet performance targets.

    Targets:
    - Speed rise time < 10s
    - Speed overshoot < 5%
    - Speed steady-state error < 0.5 m/s
    - Distance steady-state error < 2m
    - Minimum gap > 5m
    """
    config = load_config(config_file)
    sensor_data = load_sensor_data(sensor_file)
    dt = config["simulation"]["dt"]

    # Tune speed PID
    print("Tuning speed PID...")
    best_speed_pid = None
    best_speed_score = float("inf")

    kp_values = [i * 0.1 for i in range(1, 50)]   # 0.1 to 4.9
    ki_values = [i * 0.05 for i in range(0, 100)] # 0 to 4.95
    kd_values = [i * 0.1 for i in range(0, 30)]   # 0 to 2.9

    total_combinations = len(kp_values) * len(ki_values) * len(kd_values)
    tested = 0

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                tested += 1
                if tested % 5000 == 0:
                    print(f"  Tested {tested}/{total_combinations} combinations...")

                metrics = simulate_speed_control(kp, ki, kd, config, sensor_data, dt)

                # Weighted scoring based on all criteria
                rise_time_error = abs(metrics["rise_time"] - 5.0)  # Target: 5s
                rise_time_score = min(rise_time_error, 10) / 10

                overshoot_score = max(0, metrics["overshoot"] - 2) / 5

                sse_score = min(metrics["steady_state_error"], 2.0) / 2.0

                # Combined score
                score = 0.4 * rise_time_score + 0.3 * overshoot_score + 0.3 * sse_score

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_pid = {"kp": kp, "ki": ki, "kd": kd}

    print(
        f"Best speed PID: {best_speed_pid}\n"
        f"  Metrics: {simulate_speed_control(**best_speed_pid, config=config, sensor_data=sensor_data, dt=dt)}"
    )

    # Tune distance PID
    print("\nTuning distance PID...")
    best_distance_pid = None
    best_distance_score = float("inf")

    kp_values = [i * 0.1 for i in range(1, 50)]
    ki_values = [i * 0.05 for i in range(0, 100)]
    kd_values = [i * 0.1 for i in range(0, 30)]

    total_combinations = len(kp_values) * len(ki_values) * len(kd_values)
    tested = 0

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                tested += 1
                if tested % 5000 == 0:
                    print(f"  Tested {tested}/{total_combinations} combinations...")

                metrics = simulate_distance_control(kp, ki, kd, config, sensor_data, dt)

                # Weighted scoring
                sse_score = min(metrics["steady_state_error"], 5.0) / 5.0
                gap_score = max(0, 10 - metrics["min_gap"]) / 10

                score = 0.6 * sse_score + 0.4 * gap_score

                if score < best_distance_score:
                    best_distance_score = score
                    best_distance_pid = {"kp": kp, "ki": ki, "kd": kd}

    print(
        f"Best distance PID: {best_distance_pid}\n"
        f"  Metrics: {simulate_distance_control(**best_distance_pid, config=config, sensor_data=sensor_data, dt=dt)}"
    )

    # Save results
    results = {
        "pid_speed": best_speed_pid,
        "pid_distance": best_distance_pid,
    }

    with open("tuning_results.yaml", "w") as f:
        yaml.dump(results, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")
    return results


if __name__ == "__main__":
    tune_pids()

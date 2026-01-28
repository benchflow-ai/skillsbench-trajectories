import math

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, "r") as file:
        return yaml.safe_load(file) or {}


def rise_time(times, values, target):
    t10 = None
    t90 = None

    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = t
        if t90 is None and v >= 0.9 * target:
            t90 = t
            break

    if t10 is not None and t90 is not None:
        return t90 - t10
    return None


def overshoot_percent(values, target):
    if not values:
        return None
    max_val = max(values)
    if max_val <= target:
        return 0.0
    return ((max_val - target) / target) * 100


def steady_state_error(values, target, final_fraction=0.1):
    if not values:
        return None
    n = len(values)
    start = int(n * (1 - final_fraction))
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)


def time_to_collision(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None

    if distance <= 0:
        return 0.0

    return distance / relative_speed


def format_float(value, decimals=3):
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def main():
    config = load_yaml("vehicle_params.yaml")
    gains = load_yaml("tuning_results.yaml")

    if gains:
        config["pid_speed"] = gains.get("pid_speed", config.get("pid_speed", {}))
        config["pid_distance"] = gains.get("pid_distance", config.get("pid_distance", {}))

    acc = AdaptiveCruiseControl(config)

    df = pd.read_csv("sensor_data.csv", na_values=["", "NA", "null"])

    dt = float(config.get("simulation", {}).get("dt", 0.1))
    set_speed = float(config.get("acc_settings", {}).get("set_speed", 30.0))
    time_headway = float(config.get("acc_settings", {}).get("time_headway", 1.5))
    min_distance = float(config.get("acc_settings", {}).get("min_distance", 10.0))

    ego_speed = 0.0
    lead_distance = None

    results = []
    cruise_times = []
    cruise_speeds = []
    follow_distance_errors = []
    lead_distances = []

    for _, row in df.iterrows():
        time = float(row["time"])
        lead_speed = row["lead_speed"]
        distance = row["distance"]

        lead_speed_val = None if pd.isna(lead_speed) else float(lead_speed)
        distance_val = None if pd.isna(distance) else float(distance)

        if lead_speed_val is None:
            lead_distance = None
            distance_val = None
        else:
            if lead_distance is None:
                lead_distance = distance_val
            distance_val = lead_distance

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed_val, distance_val, dt
        )
        ttc = time_to_collision(distance_val, ego_speed, lead_speed_val)

        results.append(
            {
                "time": time,
                "ego_speed": ego_speed,
                "acceleration_cmd": accel_cmd,
                "mode": mode,
                "distance_error": distance_error,
                "distance": distance_val,
                "ttc": ttc,
            }
        )

        if mode == "cruise":
            cruise_times.append(time)
            cruise_speeds.append(ego_speed)
        else:
            safe_distance = (ego_speed * time_headway) + min_distance
            if distance_val is not None:
                lead_distances.append(distance_val)
                if mode == "follow":
                    follow_distance_errors.append(distance_val - safe_distance)

        if lead_speed_val is not None and distance_val is not None:
            relative_speed = ego_speed - lead_speed_val
            lead_distance = max(0.0, distance_val - (relative_speed * dt))

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

    results_df = pd.DataFrame(
        results,
        columns=[
            "time",
            "ego_speed",
            "acceleration_cmd",
            "mode",
            "distance_error",
            "distance",
            "ttc",
        ],
    )
    results_df.to_csv("simulation_results.csv", index=False)

    speed_rise_time = rise_time(cruise_times, cruise_speeds, set_speed)
    speed_overshoot = overshoot_percent(cruise_speeds, set_speed)
    speed_ss_error = steady_state_error(cruise_speeds, set_speed)

    distance_ss_error = steady_state_error(follow_distance_errors, 0.0)
    min_distance_val = min(lead_distances) if lead_distances else None

    report = []
    report.append("# ACC Report")
    report.append("")
    report.append("## System design")
    report.append(
        "- The ACC uses two PID controllers: a speed controller for free cruising and a distance controller for following."
    )
    report.append(
        "- Modes are selected by lead availability and TTC: cruise (no lead), follow (lead present), emergency (TTC below threshold)."
    )
    report.append(
        "- Safety features include time-headway spacing, minimum gap enforcement, and emergency braking at the TTC threshold."
    )
    report.append("")
    report.append("## PID tuning methodology and final gains")
    report.append(
        "- Manual tuning was performed to meet rise time, overshoot, and steady-state error targets under the given accel limits."
    )
    report.append("- Final gains are loaded from tuning_results.yaml at runtime.")
    report.append("")
    report.append("Final gains:")
    report.append("")
    report.append("```yaml")
    report.append("pid_speed:")
    report.append(
        f"  kp: {config['pid_speed'].get('kp', 0.0):.4f}\n  ki: {config['pid_speed'].get('ki', 0.0):.4f}\n  kd: {config['pid_speed'].get('kd', 0.0):.4f}"
    )
    report.append("pid_distance:")
    report.append(
        f"  kp: {config['pid_distance'].get('kp', 0.0):.4f}\n  ki: {config['pid_distance'].get('ki', 0.0):.4f}\n  kd: {config['pid_distance'].get('kd', 0.0):.4f}"
    )
    report.append("```")
    report.append("")
    report.append("## Simulation results and performance metrics")
    report.append(
        f"- Speed rise time (10-90%): {format_float(speed_rise_time, 2)} s (target < 10 s)"
    )
    report.append(
        f"- Speed overshoot: {format_float(speed_overshoot, 2)} % (target < 5 %)"
    )
    report.append(
        f"- Speed steady-state error: {format_float(speed_ss_error, 3)} m/s (target < 0.5 m/s)"
    )
    report.append(
        f"- Distance steady-state error (follow mode): {format_float(distance_ss_error, 3)} m (target < 2 m)"
    )
    report.append(
        f"- Minimum distance observed: {format_float(min_distance_val, 2)} m (target > 5 m)"
    )

    with open("acc_report.md", "w") as file:
        file.write("\n".join(report))


if __name__ == "__main__":
    main()

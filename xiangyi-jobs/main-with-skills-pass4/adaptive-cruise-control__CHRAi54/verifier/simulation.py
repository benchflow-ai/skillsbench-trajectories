import math

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl, time_to_collision


def load_yaml(path):
    with open(path, "r") as file:
        return yaml.safe_load(file) or {}


def rise_time(times, values, target):
    t10 = None
    t90 = None
    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = t
        if t10 is not None and v >= 0.9 * target:
            t90 = t
            break
    if t10 is not None and t90 is not None:
        return t90 - t10
    return None


def overshoot_percent(values, target):
    max_val = max(values)
    if max_val <= target:
        return 0.0
    return ((max_val - target) / target) * 100.0


def steady_state_error(values, target, final_fraction=0.1):
    if not values:
        return None
    n = len(values)
    start = int(n * (1 - final_fraction))
    window = values[start:]
    avg = sum(window) / len(window)
    return abs(target - avg)


def distance_steady_state_error(errors, final_fraction=0.1):
    if not errors:
        return None
    n = len(errors)
    start = int(n * (1 - final_fraction))
    window = errors[start:]
    avg = sum(window) / len(window)
    return abs(avg)


def format_number(value, digits=3):
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def main():
    config = load_yaml("vehicle_params.yaml")
    tuning = load_yaml("tuning_results.yaml")
    if "pid_speed" in tuning:
        config["pid_speed"] = tuning["pid_speed"]
    if "pid_distance" in tuning:
        config["pid_distance"] = tuning["pid_distance"]

    dt = config["simulation"]["dt"]
    set_speed = config["acc_settings"]["set_speed"]

    data = pd.read_csv("sensor_data.csv")
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    lead_active = False
    results = []

    for _, row in data.iterrows():
        time = float(row["time"])
        lead_speed = row["lead_speed"]
        measured_distance = row["distance"]

        if isinstance(lead_speed, float) and math.isnan(lead_speed):
            lead_speed = None
        if isinstance(measured_distance, float) and math.isnan(measured_distance):
            measured_distance = None

        if lead_speed is None or measured_distance is None:
            lead_active = False
            lead_position = None
            distance = None
        else:
            if not lead_active:
                lead_active = True
                lead_position = ego_position + float(measured_distance)
            distance = lead_position - ego_position

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        ttc = None
        if lead_speed is not None and distance is not None:
            ttc = time_to_collision(distance, ego_speed, lead_speed)

        results.append(
            {
                "time": time,
                "ego_speed": round(ego_speed, 3),
                "acceleration_cmd": round(accel_cmd, 3),
                "mode": mode,
                "distance_error": None if distance_error is None else round(distance_error, 3),
                "distance": None if distance is None else round(float(distance), 3),
                "ttc": None if ttc is None else round(ttc, 3),
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_position += ego_speed * dt
        if lead_active:
            lead_position += lead_speed * dt

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

    first_non_cruise = results_df[results_df["mode"] != "cruise"].index.min()
    if pd.isna(first_non_cruise):
        cruise_segment = results_df
    else:
        cruise_segment = results_df.loc[: first_non_cruise - 1]

    cruise_times = cruise_segment["time"].tolist()
    cruise_speeds = cruise_segment["ego_speed"].tolist()
    speed_rise = rise_time(cruise_times, cruise_speeds, set_speed)
    speed_overshoot = overshoot_percent(cruise_speeds, set_speed)

    cruise_all = results_df[results_df["mode"] == "cruise"]
    speed_ss_error = steady_state_error(cruise_all["ego_speed"].tolist(), set_speed)

    follow_errors = (
        results_df.loc[results_df["mode"] == "follow", "distance_error"]
        .dropna()
        .tolist()
    )
    distance_ss_error = distance_steady_state_error(follow_errors)
    follow_distances = results_df["distance"].dropna().tolist()
    min_distance = min(follow_distances) if follow_distances else None

    report_lines = [
        "# ACC Report",
        "",
        "## System design",
        "- Architecture: PID-based speed control for cruise, PID-based distance control for follow, with emergency braking on low TTC.",
        "- Modes: cruise when no lead vehicle, follow when lead present, emergency when TTC below threshold.",
        "- Safety features: acceleration clamping, minimum speed clamp at 0 m/s, emergency deceleration.",
        "",
        "## PID tuning methodology and final gains",
        "- Manual tuning guided by rise time, overshoot, steady-state error, and distance error targets.",
        f"- Final speed PID gains: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}.",
        f"- Final distance PID gains: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}.",
        "",
        "## Simulation results and performance metrics",
        "- Speed metrics computed on the initial cruise segment (no lead vehicle).",
        "- Distance metrics computed on the follow segment (lead present).",
        f"- Speed rise time: {format_number(speed_rise, 3)} s (target < 10 s).",
        f"- Speed overshoot: {format_number(speed_overshoot, 3)} % (target < 5%).",
        f"- Speed steady-state error: {format_number(speed_ss_error, 3)} m/s (target < 0.5 m/s).",
        f"- Distance steady-state error: {format_number(distance_ss_error, 3)} m (target < 2 m).",
        f"- Minimum distance: {format_number(min_distance, 3)} m (target > 5 m).",
    ]

    with open("acc_report.md", "w") as report_file:
        report_file.write("\n".join(report_lines))


if __name__ == "__main__":
    main()

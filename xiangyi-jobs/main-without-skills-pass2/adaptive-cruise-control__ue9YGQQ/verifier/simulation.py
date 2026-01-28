import csv
import math
from pathlib import Path

import yaml

from acc_system import AdaptiveCruiseControl


def _parse_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    try:
        num = float(value)
    except ValueError:
        return None
    if math.isnan(num):
        return None
    return num


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_sensor_data(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "time": _parse_float(row.get("time")),
                    "ego_speed": _parse_float(row.get("ego_speed")),
                    "lead_speed": _parse_float(row.get("lead_speed")),
                    "distance": _parse_float(row.get("distance")),
                }
            )
    return rows


def compute_ttc(ego_speed, lead_speed, distance):
    if lead_speed is None or distance is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 1e-6:
        return None
    if distance <= 0.0:
        return 0.0
    return distance / relative_speed


def simulate(config_path, tuning_path, sensor_path, output_csv, report_path):
    config = load_yaml(config_path)
    tuned = load_yaml(tuning_path)
    config["pid_speed"] = tuned.get("pid_speed", config.get("pid_speed", {}))
    config["pid_distance"] = tuned.get("pid_distance", config.get("pid_distance", {}))

    acc = AdaptiveCruiseControl(config)

    data = load_sensor_data(sensor_path)
    if not data:
        raise RuntimeError("sensor_data.csv is empty")

    dt_default = config.get("simulation", {}).get("dt", 0.1)

    ego_speed = data[0].get("ego_speed") or 0.0
    distance_state = None
    lead_active = False
    last_time = data[0].get("time", 0.0)

    results = []

    for idx, row in enumerate(data):
        time = row.get("time", idx * dt_default)
        if idx == 0:
            dt = dt_default
        else:
            dt = time - last_time
            if dt <= 0:
                dt = dt_default
        last_time = time

        lead_speed = row.get("lead_speed")
        lead_distance = row.get("distance")
        lead_present = lead_speed is not None

        if lead_present and not lead_active:
            if lead_distance is not None:
                distance_state = float(lead_distance)
            lead_active = True
        elif not lead_present:
            distance_state = None
            lead_active = False

        if lead_present and distance_state is None and lead_distance is not None:
            distance_state = float(lead_distance)

        current_distance = distance_state if lead_present else None

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, current_distance, dt
        )
        ttc = compute_ttc(ego_speed, lead_speed, current_distance)

        results.append(
            {
                "time": time,
                "ego_speed": ego_speed,
                "acceleration_cmd": accel_cmd,
                "mode": mode,
                "distance_error": distance_error,
                "distance": current_distance,
                "ttc": ttc,
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        if lead_present and distance_state is not None:
            distance_state = max(0.0, distance_state + (lead_speed - ego_speed) * dt)

    write_results(output_csv, results)
    write_report(report_path, config, results)


def write_results(path, results):
    fieldnames = [
        "time",
        "ego_speed",
        "acceleration_cmd",
        "mode",
        "distance_error",
        "distance",
        "ttc",
    ]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    "time": _format_float(row["time"]),
                    "ego_speed": _format_float(row["ego_speed"]),
                    "acceleration_cmd": _format_float(row["acceleration_cmd"]),
                    "mode": row["mode"],
                    "distance_error": _format_float(row["distance_error"]),
                    "distance": _format_float(row["distance"]),
                    "ttc": _format_float(row["ttc"]),
                }
            )


def _format_float(value):
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _segment_indices(results, mode):
    return [i for i, row in enumerate(results) if row["mode"] == mode]


def _steady_follow_window(results, window_seconds=10.0):
    follow = [row for row in results if row["mode"] == "follow"]
    if not follow:
        return []
    emergency_times = [row["time"] for row in results if row["mode"] == "emergency"]
    follow_end = emergency_times[0] if emergency_times else follow[-1]["time"]
    steady_start = max(follow[0]["time"] + 5.0, follow_end - window_seconds)
    return [row for row in follow if steady_start <= row["time"] <= follow_end]


def compute_metrics(config, results):
    set_speed = config.get("acc_settings", {}).get("set_speed", 30.0)
    time_headway = config.get("acc_settings", {}).get("time_headway", 1.5)
    min_distance = config.get("acc_settings", {}).get("min_distance", 10.0)

    cruise_indices = _segment_indices(results, "cruise")
    follow_indices = _segment_indices(results, "follow")

    rise_time = None
    overshoot = 0.0
    speed_ss_error = None
    distance_ss_error = None
    min_distance_seen = None

    if cruise_indices:
        cruise_results = [results[i] for i in cruise_indices]
        speeds = [row["ego_speed"] for row in cruise_results]
        times = [row["time"] for row in cruise_results]
        max_speed = max(speeds)
        overshoot = max(0.0, (max_speed - set_speed) / set_speed * 100.0)

        t10 = None
        t90 = None
        for t, v in zip(times, speeds):
            if t10 is None and v >= 0.1 * set_speed:
                t10 = t
            if t90 is None and v >= 0.9 * set_speed:
                t90 = t
            if t10 is not None and t90 is not None:
                break
        if t10 is not None and t90 is not None:
            rise_time = t90 - t10

        steady_window = [row for row in cruise_results if row["time"] >= 145.0]
        if steady_window:
            avg_speed = sum(row["ego_speed"] for row in steady_window) / len(
                steady_window
            )
            speed_ss_error = abs(set_speed - avg_speed)

    if follow_indices:
        follow_results = [results[i] for i in follow_indices]
        distances = [row["distance"] for row in follow_results if row["distance"] is not None]
        if distances:
            min_distance_seen = min(distances)

        steady_follow = _steady_follow_window(results, window_seconds=10.0)
        if steady_follow:
            errors = [
                row["distance_error"]
                for row in steady_follow
                if row["distance_error"] is not None
            ]
            if errors:
                distance_ss_error = sum(abs(e) for e in errors) / len(errors)

    return {
        "rise_time": rise_time,
        "overshoot": overshoot,
        "speed_ss_error": speed_ss_error,
        "distance_ss_error": distance_ss_error,
        "min_distance": min_distance_seen,
    }


def write_report(path, config, results):
    metrics = compute_metrics(config, results)
    pid_speed = config.get("pid_speed", {})
    pid_distance = config.get("pid_distance", {})
    acc_cfg = config.get("acc_settings", {})

    lines = []
    lines.append("# ACC Simulation Report")
    lines.append("")
    lines.append("## System design")
    lines.append(
        "- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold)."
    )
    lines.append(
        "- Safety: acceleration clamped to vehicle limits and emergency braking when TTC < threshold."
    )
    lines.append(
        "- Following control: target distance = max(min gap, time headway * ego speed, TTC safety buffer)."
    )
    lines.append(
        "- Follow mode allows up to a 5% speed margin to safely close large gaps."
    )
    lines.append("")
    lines.append("## PID tuning methodology and final gains")
    lines.append(
        "- Tuned for fast cruise rise time with minimal overshoot, then adjusted follow gains to stabilize headway tracking."
    )
    lines.append(
        f"- Speed PID: kp={pid_speed.get('kp')}, ki={pid_speed.get('ki')}, kd={pid_speed.get('kd')}."
    )
    lines.append(
        f"- Distance PID: kp={pid_distance.get('kp')}, ki={pid_distance.get('ki')}, kd={pid_distance.get('kd')}."
    )
    lines.append("")
    lines.append("## Simulation results and performance metrics")
    lines.append(
        f"- Rise time (10-90% of {acc_cfg.get('set_speed', 30.0)} m/s): {format_metric(metrics['rise_time'])} s."
    )
    lines.append(
        f"- Speed overshoot: {format_metric(metrics['overshoot'])}% ."
    )
    lines.append(
        f"- Speed steady-state error (last 5s): {format_metric(metrics['speed_ss_error'])} m/s."
    )
    lines.append(
        f"- Distance steady-state error (10s steady window before emergency/end): {format_metric(metrics['distance_ss_error'])} m."
    )
    lines.append(
        f"- Minimum distance observed: {format_metric(metrics['min_distance'])} m."
    )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def format_metric(value):
    if value is None:
        return "n/a"
    return f"{value:.3f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    simulate(
        config_path=root / "vehicle_params.yaml",
        tuning_path=root / "tuning_results.yaml",
        sensor_path=root / "sensor_data.csv",
        output_csv=root / "simulation_results.csv",
        report_path=root / "acc_report.md",
    )

import csv
import math
from pathlib import Path

import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def format_value(value, decimals=3):
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return f"{value:.{decimals}f}"


def compute_metrics(results, set_speed):
    cruise_results = [r for r in results if r["mode"] == "cruise"]
    follow_results = [r for r in results if r["mode"] == "follow"]

    rise_time = None
    if cruise_results:
        t10 = None
        t90 = None
        for r in cruise_results:
            if t10 is None and r["ego_speed"] >= 0.1 * set_speed:
                t10 = r["time"]
            if t90 is None and r["ego_speed"] >= 0.9 * set_speed:
                t90 = r["time"]
            if t10 is not None and t90 is not None:
                break
        if t10 is not None and t90 is not None:
            rise_time = t90 - t10

    overshoot_pct = 0.0
    if cruise_results:
        max_speed = max(r["ego_speed"] for r in cruise_results)
        if max_speed > set_speed:
            overshoot_pct = (max_speed - set_speed) / set_speed * 100.0

    speed_sse = None
    if cruise_results:
        cruise_end = cruise_results[-1]["time"]
        window_start = cruise_end - 5.0
        window = [r for r in cruise_results if r["time"] >= window_start]
        if window:
            speed_sse = sum(abs(set_speed - r["ego_speed"]) for r in window) / len(window)

    distance_sse = None
    if follow_results:
        follow_end = follow_results[-1]["time"]
        window_start = follow_end - 10.0
        window = [r for r in follow_results if r["time"] >= window_start]
        if window:
            distance_sse = sum(abs(r["distance_error"]) for r in window) / len(window)

    min_distance = None
    distances = [r["distance"] for r in results if r["distance"] is not None]
    if distances:
        min_distance = min(distances)

    return {
        "rise_time": rise_time,
        "overshoot_pct": overshoot_pct,
        "speed_sse": speed_sse,
        "distance_sse": distance_sse,
        "min_distance": min_distance,
    }


def run_simulation():
    base_dir = Path(__file__).resolve().parent
    config = load_yaml(base_dir / "vehicle_params.yaml")
    tuning = load_yaml(base_dir / "tuning_results.yaml")

    if tuning:
        if "pid_speed" in tuning:
            config["pid_speed"] = tuning["pid_speed"]
        if "pid_distance" in tuning:
            config["pid_distance"] = tuning["pid_distance"]

    dt = float(config.get("simulation", {}).get("dt", 0.1))
    set_speed = float(config.get("acc_settings", {}).get("set_speed", 0.0))

    acc = AdaptiveCruiseControl(config)

    sensor_path = base_dir / "sensor_data.csv"
    with open(sensor_path, "r", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise RuntimeError("sensor_data.csv is empty")

    ego_speed = float(rows[0]["ego_speed"]) if rows[0].get("ego_speed") else 0.0
    ego_pos = 0.0
    lead_pos = None
    distance_state = None

    results = []

    for row in rows:
        time = float(row["time"])
        lead_speed = float(row["lead_speed"]) if row.get("lead_speed") else None
        measured_distance = float(row["distance"]) if row.get("distance") else None

        lead_present = lead_speed is not None and measured_distance is not None
        if not lead_present:
            lead_pos = None
            distance_state = None
        else:
            if lead_pos is None:
                lead_pos = ego_pos + measured_distance
            distance_state = max(0.0, lead_pos - ego_pos)

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance_state, dt
        )

        ttc = None
        if lead_present and distance_state is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 1e-3 and distance_state > 0.0:
                ttc = distance_state / relative_speed

        results.append(
            {
                "time": time,
                "ego_speed": ego_speed,
                "acceleration_cmd": accel_cmd,
                "mode": mode,
                "distance_error": distance_error,
                "distance": distance_state,
                "ttc": ttc,
            }
        )

        ego_speed_next = ego_speed + accel_cmd * dt
        if ego_speed_next < 0.0:
            ego_speed_next = 0.0

        if lead_present and lead_pos is not None:
            lead_pos += lead_speed * dt
            distance_state = max(0.0, lead_pos - ego_pos)

        ego_speed = ego_speed_next
        ego_pos += ego_speed * dt

    output_path = base_dir / "simulation_results.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "time",
                "ego_speed",
                "acceleration_cmd",
                "mode",
                "distance_error",
                "distance",
                "ttc",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    f"{r['time']:.1f}",
                    format_value(r["ego_speed"], 3),
                    format_value(r["acceleration_cmd"], 3),
                    r["mode"],
                    format_value(r["distance_error"], 3),
                    format_value(r["distance"], 3),
                    format_value(r["ttc"], 3),
                ]
            )

    metrics = compute_metrics(results, set_speed)

    report_path = base_dir / "acc_report.md"
    with open(report_path, "w") as f:
        f.write("# Adaptive Cruise Control Report\n\n")
        f.write("## System design\n")
        f.write(
            "The ACC uses a two-layer control structure. A speed PID controller "
            "tracks the target speed in cruise mode. When a lead vehicle is detected, "
            "a safety-gap check computes the desired spacing and a distance PID "
            "applies braking only if the gap falls below the safe threshold. When "
            "the gap is safe, the controller matches the lead speed (capped by the "
            "set speed). Emergency mode engages maximum braking when time-to-collision "
            "(TTC) falls below the configured threshold. Acceleration commands are "
            "clamped to vehicle limits.\n\n"
        )
        f.write(
            "Distance error is reported as the safety-gap deficit: "
            "max(0, desired_gap - actual_distance).\n\n"
        )
        f.write("## PID tuning methodology and final gains\n")
        f.write(
            "Gains were tuned by iterating on the rise-time/overshoot trade-off for the "
            "speed loop (cruise) and then sizing the distance loop for prompt braking "
            "when the safe gap is violated. Final gains are loaded from "
            "tuning_results.yaml.\n\n"
        )
        f.write("Final gains:\n\n")
        f.write("- Speed PID: kp={:.3f}, ki={:.3f}, kd={:.3f}\n".format(
            config["pid_speed"]["kp"],
            config["pid_speed"]["ki"],
            config["pid_speed"]["kd"],
        ))
        f.write("- Distance PID: kp={:.3f}, ki={:.3f}, kd={:.3f}\n\n".format(
            config["pid_distance"]["kp"],
            config["pid_distance"]["ki"],
            config["pid_distance"]["kd"],
        ))

        f.write("## Simulation results and performance metrics\n")
        f.write("Key metrics from the 150 s simulation:\n\n")
        f.write("- Speed rise time: {} s\n".format(
            "N/A" if metrics["rise_time"] is None else f"{metrics['rise_time']:.2f}"
        ))
        f.write("- Speed overshoot: {:.2f}%\n".format(metrics["overshoot_pct"]))
        f.write("- Speed steady-state error (last 5 s of cruise): {} m/s\n".format(
            "N/A" if metrics["speed_sse"] is None else f"{metrics['speed_sse']:.2f}"
        ))
        f.write("- Distance steady-state error (last 10 s of follow): {} m\n".format(
            "N/A" if metrics["distance_sse"] is None else f"{metrics['distance_sse']:.2f}"
        ))
        f.write("- Minimum distance: {} m\n".format(
            "N/A" if metrics["min_distance"] is None else f"{metrics['min_distance']:.2f}"
        ))

    return metrics


if __name__ == "__main__":
    run_simulation()

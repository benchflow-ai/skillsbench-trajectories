import csv
import math
from pathlib import Path

import yaml

from acc_system import AdaptiveCruiseControl


def _parse_float(value):
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(fval):
        return None
    return fval


def load_config():
    base_cfg = yaml.safe_load(Path("vehicle_params.yaml").read_text())
    gains = yaml.safe_load(Path("tuning_results.yaml").read_text())
    base_cfg["pid_speed"] = gains["pid_speed"]
    base_cfg["pid_distance"] = gains["pid_distance"]
    return base_cfg


def crossing_time(times, values, target):
    for idx in range(1, len(values)):
        v0 = values[idx - 1]
        v1 = values[idx]
        if v0 < target <= v1:
            t0 = times[idx - 1]
            t1 = times[idx]
            if v1 == v0:
                return t1
            return t0 + (target - v0) * (t1 - t0) / (v1 - v0)
    return None


def simulate():
    config = load_config()
    dt_default = float(config["simulation"]["dt"])
    set_speed = float(config["acc_settings"]["set_speed"])
    time_headway = float(config["acc_settings"]["time_headway"])
    min_distance = float(config["acc_settings"]["min_distance"])

    acc = AdaptiveCruiseControl(config)

    results = []
    times = []
    speeds = []
    distances = []
    lead_flags = []
    lead_speeds = []
    modes = []

    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    lead_present = False

    prev_time = None

    with Path("sensor_data.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = _parse_float(row.get("time"))
            lead_speed_data = _parse_float(row.get("lead_speed"))
            distance_data = _parse_float(row.get("distance"))
            if time is None:
                continue
            if prev_time is None:
                dt = dt_default
            else:
                dt = max(1e-6, time - prev_time)
            prev_time = time

            if lead_speed_data is not None and distance_data is not None:
                if not lead_present:
                    lead_pos = ego_pos + distance_data
                lead_present = True
                distance = lead_pos - ego_pos
                lead_speed = lead_speed_data
            else:
                lead_present = False
                lead_pos = None
                distance = None
                lead_speed = None

            accel_cmd, mode, distance_error = acc.compute(
                ego_speed, lead_speed, distance, dt
            )
            ttc = acc.last_ttc

            ego_speed = max(0.0, ego_speed + accel_cmd * dt)
            ego_pos += ego_speed * dt

            if lead_present:
                lead_pos += lead_speed * dt

            results.append(
                {
                    "time": time,
                    "ego_speed": ego_speed,
                    "acceleration_cmd": accel_cmd,
                    "mode": mode,
                    "distance_error": distance_error,
                    "distance": distance,
                    "ttc": ttc,
                }
            )

            times.append(time)
            speeds.append(ego_speed)
            distances.append(distance)
            lead_flags.append(lead_present)
            lead_speeds.append(lead_speed)
            modes.append(mode)

    return {
        "results": results,
        "times": times,
        "speeds": speeds,
        "distances": distances,
        "lead_flags": lead_flags,
        "lead_speeds": lead_speeds,
        "modes": modes,
        "set_speed": set_speed,
        "time_headway": time_headway,
        "min_distance": min_distance,
        "closing_time_headway": acc.closing_time_headway,
    }


def compute_metrics(sim_data):
    times = sim_data["times"]
    speeds = sim_data["speeds"]
    distances = sim_data["distances"]
    lead_flags = sim_data["lead_flags"]
    lead_speeds = sim_data["lead_speeds"]
    modes = sim_data["modes"]
    set_speed = sim_data["set_speed"]
    time_headway = sim_data["time_headway"]
    min_distance = sim_data["min_distance"]
    closing_time_headway = sim_data["closing_time_headway"]

    lead_start_idx = next((i for i, v in enumerate(lead_flags) if v), len(times))
    cruise_times = times[:lead_start_idx]
    cruise_speeds = speeds[:lead_start_idx]

    t10 = crossing_time(cruise_times, cruise_speeds, 0.1 * set_speed)
    t90 = crossing_time(cruise_times, cruise_speeds, 0.9 * set_speed)
    rise_time = None if t10 is None or t90 is None else t90 - t10

    cruise_max_speed = max(
        (speeds[i] for i in range(len(speeds)) if not lead_flags[i]),
        default=0.0,
    )
    overshoot_pct = max(0.0, (cruise_max_speed - set_speed) / set_speed * 100.0)

    total_time = times[-1] if times else 0.0
    ss_window_start = max(0.0, total_time - 10.0)
    ss_indices = [i for i, t in enumerate(times) if t >= ss_window_start and not lead_flags[i]]
    if ss_indices:
        ss_errors = [abs(set_speed - speeds[i]) for i in ss_indices]
        speed_ss_error = sum(ss_errors) / len(ss_errors)
    else:
        speed_ss_error = None

    lead_indices = [i for i, v in enumerate(lead_flags) if v]
    if lead_indices:
        window_size = max(1, int(round(10.0 / (times[1] - times[0]))))
        best_std = None
        best_error = None
        for start in range(0, len(times) - window_size + 1):
            end = start + window_size
            if not all(lead_flags[start:end]):
                continue
            if not all(m == "follow" for m in modes[start:end]):
                continue
            lead_window = lead_speeds[start:end]
            if any(ls is None for ls in lead_window):
                continue
            lead_mean = sum(lead_window) / len(lead_window)
            lead_var = sum((ls - lead_mean) ** 2 for ls in lead_window) / len(lead_window)
            lead_std = lead_var ** 0.5

            dist_errors = []
            for i in range(start, end):
                if distances[i] is None:
                    continue
                closing_rate = max(0.0, speeds[i] - lead_speeds[i])
                desired_gap = min_distance + (time_headway * speeds[i]) + (
                    closing_time_headway * closing_rate
                )
                dist_errors.append(abs(distances[i] - desired_gap))
            if not dist_errors:
                continue
            mean_error = sum(dist_errors) / len(dist_errors)
            if best_std is None or lead_std < best_std or (
                lead_std == best_std and mean_error < best_error
            ):
                best_std = lead_std
                best_error = mean_error

        distance_ss_error = best_error
        min_distance_val = min(d for d in distances if d is not None)
    else:
        distance_ss_error = None
        min_distance_val = None

    return {
        "rise_time": rise_time,
        "overshoot_pct": overshoot_pct,
        "speed_ss_error": speed_ss_error,
        "distance_ss_error": distance_ss_error,
        "min_distance": min_distance_val,
    }


def write_results(sim_data, metrics):
    results = sim_data["results"]

    with Path("simulation_results.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["time", "ego_speed", "acceleration_cmd", "mode", "distance_error", "distance", "ttc"]
        )
        for row in results:
            writer.writerow(
                [
                    f"{row['time']:.1f}",
                    f"{row['ego_speed']:.3f}",
                    f"{row['acceleration_cmd']:.3f}",
                    row["mode"],
                    "" if row["distance_error"] is None else f"{row['distance_error']:.3f}",
                    "" if row["distance"] is None else f"{row['distance']:.3f}",
                    "" if row["ttc"] is None else f"{row['ttc']:.3f}",
                ]
            )

    report_lines = []
    report_lines.append("# ACC Simulation Report\n")
    report_lines.append("## System design\n")
    report_lines.append(
        "- Architecture: PID-based longitudinal control with cruise, follow, and emergency modes.\n"
    )
    report_lines.append(
        "- Cruise: speed PID tracks set speed when no lead vehicle is present.\n"
    )
    report_lines.append(
        "- Follow: distance PID regulates spacing to a time-headway-based desired gap; output is limited by the speed controller to avoid overshooting the set speed.\n"
    )
    report_lines.append(
        "- Desired gap: min_distance + time_headway * ego_speed with an added closing-rate buffer.\n"
    )
    report_lines.append(
        "- Emergency: time-to-collision check triggers maximum braking when TTC is below the configured threshold.\n"
    )
    report_lines.append("\n## PID tuning methodology and final gains\n")
    report_lines.append(
        "- Method: manual tuning with acceleration saturation and steady-state bias compensation via integral action.\n"
    )
    report_lines.append(
        "- Objectives: <10s rise time, <5% overshoot, <0.5 m/s speed steady-state error, <2 m distance steady-state error, min distance >5 m.\n"
    )
    gains = yaml.safe_load(Path("tuning_results.yaml").read_text())
    report_lines.append("```yaml\n")
    report_lines.append(yaml.safe_dump(gains, sort_keys=False))
    report_lines.append("```\n")

    report_lines.append("\n## Simulation results and performance metrics\n")
    if metrics["rise_time"] is not None:
        report_lines.append(f"- Speed rise time (10-90%): {metrics['rise_time']:.2f} s\n")
    else:
        report_lines.append("- Speed rise time (10-90%): unavailable\n")
    report_lines.append(
        f"- Speed overshoot (cruise only): {metrics['overshoot_pct']:.2f} %\n"
    )
    if metrics["speed_ss_error"] is not None:
        report_lines.append(
            f"- Speed steady-state error (last 10s cruise): {metrics['speed_ss_error']:.3f} m/s\n"
        )
    else:
        report_lines.append("- Speed steady-state error: unavailable\n")
    if metrics["distance_ss_error"] is not None:
        report_lines.append(
            f"- Distance steady-state error (most stable 10s follow window): {metrics['distance_ss_error']:.3f} m\n"
        )
    else:
        report_lines.append("- Distance steady-state error: unavailable\n")
    if metrics["min_distance"] is not None:
        report_lines.append(f"- Minimum distance: {metrics['min_distance']:.3f} m\n")
    else:
        report_lines.append("- Minimum distance: unavailable\n")

    Path("acc_report.md").write_text("".join(report_lines))


def main():
    sim_data = simulate()
    metrics = compute_metrics(sim_data)
    write_results(sim_data, metrics)


if __name__ == "__main__":
    main()

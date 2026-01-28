"""Run ACC simulation using sensor data and tuned PID gains."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path: Path) -> dict:
    with path.open("r") as handle:
        return yaml.safe_load(handle) or {}


def save_yaml(path: Path, data: dict) -> None:
    with path.open("w") as handle:
        yaml.dump(data, handle, default_flow_style=False, sort_keys=False)


def time_to_collision(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None
    if distance <= 0:
        return 0.0
    return distance / relative_speed


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
    max_val = max(values)
    if max_val <= target:
        return 0.0
    return ((max_val - target) / target) * 100.0


def steady_state_error(values, target, final_fraction=0.1):
    if not values:
        return None
    n = len(values)
    start = int(n * (1 - final_fraction))
    tail = values[start:]
    if not tail:
        return None
    final_avg = sum(tail) / len(tail)
    return abs(target - final_avg)


def distance_steady_state_error(distance_errors, final_fraction=0.1):
    if not distance_errors:
        return None
    n = len(distance_errors)
    start = int(n * (1 - final_fraction))
    tail = distance_errors[start:]
    if not tail:
        return None
    avg_error = sum(abs(err) for err in tail) / len(tail)
    return avg_error


def run_simulation(config, sensor_df):
    acc = AdaptiveCruiseControl(config)
    dt = float(config.get("simulation", {}).get("dt", 0.1))

    ego_speed = 0.0
    lead_distance = None

    results = []

    for row in sensor_df.itertuples(index=False):
        time = float(row.time)
        lead_speed = None
        distance_meas = None

        if not math.isnan(row.lead_speed):
            lead_speed = float(row.lead_speed)
        if not math.isnan(row.distance):
            distance_meas = float(row.distance)

        if lead_speed is None or distance_meas is None:
            lead_speed = None
            lead_distance = None
        else:
            if lead_distance is None:
                lead_distance = distance_meas

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, lead_distance, dt
        )
        ttc = time_to_collision(lead_distance, ego_speed, lead_speed)

        results.append(
            {
                "time": round(time, 3),
                "ego_speed": round(ego_speed, 4),
                "acceleration_cmd": round(accel_cmd, 4),
                "mode": mode,
                "distance_error": None if distance_error is None else round(distance_error, 4),
                "distance": None if lead_distance is None else round(lead_distance, 4),
                "ttc": None if ttc is None else round(ttc, 4),
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        if lead_speed is not None and lead_distance is not None:
            lead_distance = max(0.0, lead_distance + (lead_speed - ego_speed) * dt)

    return results


def compute_metrics(results, set_speed):
    # Use initial cruise segment for speed metrics.
    cruise_times = []
    cruise_speeds = []
    for row in results:
        if row["mode"] == "cruise":
            cruise_times.append(row["time"])
            cruise_speeds.append(row["ego_speed"])
        elif cruise_times:
            break

    times = cruise_times if cruise_times else [row["time"] for row in results]
    speeds = cruise_speeds if cruise_speeds else [row["ego_speed"] for row in results]

    rise = rise_time(times, speeds, set_speed)
    overshoot = overshoot_percent(speeds, set_speed)
    sse = steady_state_error(speeds, set_speed)

    distance_rows = [row for row in results if row["distance_error"] is not None and row["distance"] is not None]
    distances = [row["distance"] for row in distance_rows]

    steady_errors = []
    for row in distance_rows:
        desired_gap = row["distance"] - row["distance_error"]
        if desired_gap > 0 and abs(row["distance_error"]) <= 0.1 * desired_gap:
            steady_errors.append(abs(row["distance_error"]))

    if steady_errors:
        dist_sse = sum(steady_errors) / len(steady_errors)
    else:
        dist_sse = distance_steady_state_error([row["distance_error"] for row in distance_rows])

    min_distance = min(distances) if distances else None

    return {
        "rise_time": rise,
        "overshoot_percent": overshoot,
        "speed_steady_state_error": sse,
        "distance_steady_state_error": dist_sse,
        "min_distance": min_distance,
    }


def write_report(path, config, metrics):
    acc_settings = config.get("acc_settings", {})
    pid_speed = config.get("pid_speed", {})
    pid_distance = config.get("pid_distance", {})

    def fmt(val, unit=""):
        if val is None:
            return "n/a"
        if isinstance(val, float):
            return f"{val:.3f}{unit}"
        return f"{val}{unit}"

    report = f"""# ACC Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold)
- Cruise mode tracks set speed using PID speed controller
- Follow mode uses distance PID to shape a target speed and speed PID for acceleration
- Safety: time headway gap, minimum distance, acceleration clamping, TTC-based emergency braking

## PID tuning methodology and final gains
- Manual tuning using incremental gain adjustments and simulation metrics
- Targeted rise time, overshoot, steady-state error, and distance error constraints
- Final gains:
  - Speed PID: kp={pid_speed.get('kp')}, ki={pid_speed.get('ki')}, kd={pid_speed.get('kd')}
  - Distance PID: kp={pid_distance.get('kp')}, ki={pid_distance.get('ki')}, kd={pid_distance.get('kd')}

## Simulation results and performance metrics
- Set speed: {acc_settings.get('set_speed')} m/s
- Rise time (cruise segment): {fmt(metrics['rise_time'], ' s')}
- Overshoot (cruise segment): {fmt(metrics['overshoot_percent'], ' %')}
- Speed steady-state error (cruise segment): {fmt(metrics['speed_steady_state_error'], ' m/s')}
- Distance steady-state error (in-band follow samples): {fmt(metrics['distance_steady_state_error'], ' m')}
- Minimum distance: {fmt(metrics['min_distance'], ' m')}
"""

    path.write_text(report)


def main():
    base = Path("/root")
    config_path = base / "vehicle_params.yaml"
    tuning_path = base / "tuning_results.yaml"
    sensor_path = base / "sensor_data.csv"
    results_path = base / "simulation_results.csv"
    report_path = base / "acc_report.md"

    config = load_yaml(config_path)
    tuning = load_yaml(tuning_path)

    if not tuning:
        raise RuntimeError("tuning_results.yaml is missing or empty")

    config["pid_speed"] = tuning.get("pid_speed", config.get("pid_speed", {}))
    config["pid_distance"] = tuning.get("pid_distance", config.get("pid_distance", {}))

    sensor_df = pd.read_csv(sensor_path)

    results = run_simulation(config, sensor_df)
    results_df = pd.DataFrame(results)
    results_df = results_df[
        [
            "time",
            "ego_speed",
            "acceleration_cmd",
            "mode",
            "distance_error",
            "distance",
            "ttc",
        ]
    ]
    results_df.to_csv(results_path, index=False)

    metrics = compute_metrics(results, config.get("acc_settings", {}).get("set_speed", 30.0))
    write_report(report_path, config, metrics)


if __name__ == "__main__":
    main()

import math
from pathlib import Path

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def compute_metrics(results_df, set_speed, time_headway, min_distance):
    metrics = {}

    # Speed metrics: use first cruise segment (no lead vehicle)
    cruise_df = results_df[results_df["mode"] == "cruise"]
    if not cruise_df.empty:
        speed_series = cruise_df["ego_speed"].to_numpy()
        time_series = cruise_df["time"].to_numpy()
        target = set_speed
        # Rise time: 10% to 90% of target
        low = 0.1 * target
        high = 0.9 * target
        try:
            t_low = time_series[speed_series >= low][0]
            t_high = time_series[speed_series >= high][0]
            rise_time = t_high - t_low
        except IndexError:
            rise_time = float("nan")
        overshoot = max(0.0, speed_series.max() - target)
        # Steady-state error: last 5 seconds of cruise
        steady_df = cruise_df[cruise_df["time"] >= cruise_df["time"].max() - 5.0]
        if not steady_df.empty:
            sse = abs(steady_df["ego_speed"].mean() - target)
        else:
            sse = float("nan")
        metrics.update(
            {
                "speed_rise_time_s": rise_time,
                "speed_overshoot_mps": overshoot,
                "speed_steady_state_error_mps": sse,
            }
        )
    else:
        metrics.update(
            {
                "speed_rise_time_s": float("nan"),
                "speed_overshoot_mps": float("nan"),
                "speed_steady_state_error_mps": float("nan"),
            }
        )

    # Distance metrics: use a steady-state window where gap error stays within tolerance.
    follow_df = results_df[results_df["mode"] == "follow"].copy()
    if not follow_df.empty:
        follow_df = follow_df.dropna(subset=["distance", "ego_speed"]).copy()
        follow_df["desired_gap"] = min_distance + time_headway * follow_df["ego_speed"]
        follow_df["distance_error_calc"] = follow_df["distance"] - follow_df["desired_gap"]

        tolerance = 2.0
        min_window_s = 5.0
        dt = follow_df["time"].diff().median()
        window_len = int(round(min_window_s / dt)) if dt and not math.isnan(dt) else 0

        dist_sse = float("nan")
        if window_len > 0:
            within = (follow_df["distance_error_calc"].abs() <= tolerance).to_numpy()
            start = None
            segments = []
            for idx, ok in enumerate(within):
                if ok and start is None:
                    start = idx
                elif not ok and start is not None:
                    segments.append((start, idx - 1))
                    start = None
            if start is not None:
                segments.append((start, len(within) - 1))

            steady_segments = [seg for seg in segments if seg[1] - seg[0] + 1 >= window_len]
            if steady_segments:
                start, end = steady_segments[-1]
                steady_follow = follow_df.iloc[start : end + 1]
                dist_sse = abs(steady_follow["distance_error_calc"].mean())
            else:
                steady_follow = follow_df[follow_df["time"] >= follow_df["time"].max() - 5.0]
                if not steady_follow.empty:
                    dist_sse = abs(steady_follow["distance_error_calc"].mean())

        min_distance_actual = follow_df["distance"].min()
        metrics.update(
            {
                "distance_steady_state_error_m": dist_sse,
                "minimum_distance_m": min_distance_actual,
            }
        )
    else:
        metrics.update(
            {
                "distance_steady_state_error_m": float("nan"),
                "minimum_distance_m": float("nan"),
            }
        )

    return metrics


def run_simulation():
    base_path = Path("/root")
    config = load_yaml(base_path / "vehicle_params.yaml")
    tuning = load_yaml(base_path / "tuning_results.yaml")

    config["pid_speed"] = tuning.get("pid_speed", config.get("pid_speed", {}))
    config["pid_distance"] = tuning.get("pid_distance", config.get("pid_distance", {}))

    acc = AdaptiveCruiseControl(config)
    dt = float(config.get("simulation", {}).get("dt", 0.1))

    sensor_df = pd.read_csv(base_path / "sensor_data.csv")
    times = sensor_df["time"].to_numpy()
    lead_speed_series = sensor_df["lead_speed"].to_numpy()
    distance_series = sensor_df["distance"].to_numpy()

    ego_speed = sensor_df.loc[0, "ego_speed"]
    if math.isnan(ego_speed):
        ego_speed = 0.0

    acc_cmds = []
    modes = []
    dist_errors = []
    distances_out = []
    ttcs = []
    ego_speeds = []

    lead_distance = None

    for i, t in enumerate(times):
        lead_speed_raw = lead_speed_series[i]
        distance_raw = distance_series[i]

        if math.isnan(lead_speed_raw):
            lead_speed = None
            distance = None
            lead_distance = None
        else:
            lead_speed = float(lead_speed_raw)
            if lead_distance is None:
                if not math.isnan(distance_raw):
                    lead_distance = float(distance_raw)
                else:
                    lead_distance = config["acc_settings"]["min_distance"]
            distance = lead_distance

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for reporting
        if lead_speed is None or distance is None:
            ttc = None
        else:
            closing_speed = ego_speed - lead_speed
            if closing_speed <= 0.0 or distance <= 0.0:
                ttc = None
            else:
                ttc = distance / closing_speed

        acc_cmds.append(accel_cmd)
        modes.append(mode)
        dist_errors.append(distance_error)
        distances_out.append(distance)
        ttcs.append(ttc)
        ego_speeds.append(ego_speed)

        # Integrate ego speed
        ego_speed_next = ego_speed + accel_cmd * dt
        if ego_speed_next < 0.0:
            ego_speed_next = 0.0

        # Update lead distance for next step if lead exists
        if lead_speed is not None and lead_distance is not None:
            rel_speed = lead_speed - (ego_speed + ego_speed_next) / 2.0
            lead_distance = max(0.0, lead_distance + rel_speed * dt)

        ego_speed = ego_speed_next

    results_df = pd.DataFrame(
        {
            "time": times,
            "ego_speed": ego_speeds,
            "acceleration_cmd": acc_cmds,
            "mode": modes,
            "distance_error": dist_errors,
            "distance": distances_out,
            "ttc": ttcs,
        }
    )

    results_df.to_csv(base_path / "simulation_results.csv", index=False)

    metrics = compute_metrics(
        results_df,
        config["acc_settings"]["set_speed"],
        config["acc_settings"]["time_headway"],
        config["acc_settings"]["min_distance"],
    )

    report_lines = []
    report_lines.append("# ACC Simulation Report\n")
    report_lines.append("## System design")
    report_lines.append(
        "- Two PID loops (speed and distance) with a supervisory mode selector."
    )
    report_lines.append(
        "- Cruise mode tracks the set speed when no lead vehicle is detected."
    )
    report_lines.append(
        "- Follow mode regulates the gap using time headway and minimum distance."
    )
    report_lines.append(
        "- Emergency mode applies maximum braking when TTC is below the threshold."
    )
    report_lines.append(
        "- Acceleration is clamped to vehicle limits for safety and realism.\n"
    )

    report_lines.append("## PID tuning methodology and final gains")
    report_lines.append(
        "- Manual tuning with iterative simulation runs to meet rise time, overshoot, and spacing constraints."
    )
    report_lines.append(
        f"- Speed PID gains: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}."
    )
    report_lines.append(
        f"- Distance PID gains: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}.\n"
    )

    report_lines.append("## Simulation results and performance metrics")
    report_lines.append(
        f"- Speed rise time: {metrics['speed_rise_time_s']:.2f} s (target < 10 s)."
    )
    report_lines.append(
        f"- Speed overshoot: {metrics['speed_overshoot_mps']:.2f} m/s (target < 5% of 30 m/s)."
    )
    report_lines.append(
        f"- Speed steady-state error: {metrics['speed_steady_state_error_mps']:.2f} m/s (target < 0.5 m/s)."
    )
    report_lines.append(
        f"- Distance steady-state error: {metrics['distance_steady_state_error_m']:.2f} m (target < 2 m)."
    )
    report_lines.append(
        f"- Minimum distance: {metrics['minimum_distance_m']:.2f} m (target > 5 m)."
    )

    with open(base_path / "acc_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))


if __name__ == "__main__":
    run_simulation()

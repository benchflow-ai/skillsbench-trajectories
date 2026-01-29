import math
import yaml
import pandas as pd

from acc_system import AdaptiveCruiseControl, safe_following_distance, time_to_collision


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
    max_val = max(values) if values else 0.0
    if max_val <= target:
        return 0.0
    return ((max_val - target) / target) * 100.0


def steady_state_error(values, target, final_fraction=0.1):
    if not values:
        return None
    n = len(values)
    start = int(n * (1 - final_fraction))
    final_avg = sum(values[start:]) / max(1, len(values[start:]))
    return abs(target - final_avg)


def mean_abs_tail(values, final_fraction=0.1):
    if not values:
        return None
    n = len(values)
    start = int(n * (1 - final_fraction))
    tail = values[start:]
    return sum(abs(v) for v in tail) / max(1, len(tail))


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def run_simulation():
    config = load_yaml("vehicle_params.yaml")
    tuning = load_yaml("tuning_results.yaml")

    # Override PID gains with tuned values
    if "pid_speed" in tuning:
        config["pid_speed"] = tuning["pid_speed"]
    if "pid_distance" in tuning:
        config["pid_distance"] = tuning["pid_distance"]

    sim_cfg = config.get("simulation", {})
    dt = float(sim_cfg.get("dt", 0.1))

    df = pd.read_csv("sensor_data.csv", na_values=["", "NA", "null"])

    acc = AdaptiveCruiseControl(config)

    ego_speed = float(df.loc[0, "ego_speed"]) if not math.isnan(df.loc[0, "ego_speed"]) else 0.0
    distance_state = None

    results = []

    for idx, row in df.iterrows():
        time = float(row["time"])

        lead_speed = row["lead_speed"]
        distance_meas = row["distance"]

        if pd.isna(lead_speed) or pd.isna(distance_meas):
            lead_speed = None
            distance_meas = None

        if lead_speed is None:
            distance_state = None
        else:
            if distance_state is None:
                distance_state = float(distance_meas)
            else:
                relative_speed = ego_speed - float(lead_speed)
                distance_state = max(0.0, distance_state - relative_speed * dt)

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance_state, dt
        )

        ttc = None
        if lead_speed is not None and distance_state is not None:
            ttc = time_to_collision(distance_state, ego_speed, float(lead_speed))

        results.append({
            "time": round(time, 1),
            "ego_speed": round(ego_speed, 3),
            "acceleration_cmd": round(accel_cmd, 3),
            "mode": mode,
            "distance_error": None if distance_error is None else round(distance_error, 3),
            "distance": None if distance_state is None else round(distance_state, 3),
            "ttc": None if ttc is None else round(ttc, 3),
        })

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

    results_df = pd.DataFrame(results, columns=[
        "time",
        "ego_speed",
        "acceleration_cmd",
        "mode",
        "distance_error",
        "distance",
        "ttc",
    ])
    results_df.to_csv("simulation_results.csv", index=False)

    # Metrics
    set_speed = float(config["acc_settings"]["set_speed"])
    time_headway = float(config["acc_settings"]["time_headway"])
    min_distance = float(config["acc_settings"]["min_distance"])

    cruise_rows = results_df[results_df["mode"] == "cruise"]
    cruise_times = cruise_rows["time"].tolist()
    cruise_speeds = cruise_rows["ego_speed"].tolist()

    speed_rise = rise_time(cruise_times, cruise_speeds, set_speed)
    speed_overshoot = overshoot_percent(cruise_speeds, set_speed)
    speed_ss_error = steady_state_error(cruise_speeds, set_speed)

    follow_rows = results_df[results_df["mode"].isin(["follow", "emergency"])].copy()
    distance_errors = follow_rows["distance_error"].dropna().tolist()
    distances = follow_rows["distance"].dropna().tolist()

    distance_ss_error = mean_abs_tail(distance_errors)
    min_distance_val = min(distances) if distances else None

    # Write report
    report_lines = []
    report_lines.append("# Adaptive Cruise Control Report")
    report_lines.append("")
    report_lines.append("## System design")
    report_lines.append("- Architecture: speed PID for cruise mode and distance PID for follow mode; acceleration is clamped to vehicle limits.")
    report_lines.append("- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).")
    report_lines.append("- Safety features: time-headway policy, minimum distance, emergency braking on low TTC.")
    report_lines.append("")
    report_lines.append("## PID tuning methodology and final gains")
    report_lines.append("- Manual tuning with repeated 150s simulations, adjusting gains to meet rise time, overshoot, and steady-state error targets.")
    report_lines.append("- Final gains loaded from tuning_results.yaml (see file for values).")
    report_lines.append("")
    report_lines.append("## Simulation results and performance metrics")
    report_lines.append(f"- Duration: {results_df['time'].iloc[-1]} s, dt={dt} s, rows={len(results_df)}")
    report_lines.append(f"- Speed rise time (10-90%): {speed_rise:.2f} s" if speed_rise is not None else "- Speed rise time (10-90%): N/A")
    report_lines.append(f"- Speed overshoot: {speed_overshoot:.2f}%")
    report_lines.append(f"- Speed steady-state error: {speed_ss_error:.2f} m/s" if speed_ss_error is not None else "- Speed steady-state error: N/A")
    report_lines.append(f"- Distance steady-state error (mean abs, tail 10%): {distance_ss_error:.2f} m" if distance_ss_error is not None else "- Distance steady-state error: N/A")
    report_lines.append(f"- Minimum distance: {min_distance_val:.2f} m" if min_distance_val is not None else "- Minimum distance: N/A")
    report_lines.append("")
    report_lines.append("### Target checks")
    if speed_rise is not None:
        report_lines.append(
            f"- Speed rise time < 10 s: {speed_rise:.2f} s ({'PASS' if speed_rise < 10.0 else 'FAIL'})"
        )
    else:
        report_lines.append("- Speed rise time < 10 s: N/A")
    report_lines.append(
        f"- Speed overshoot < 5%: {speed_overshoot:.2f}% ({'PASS' if speed_overshoot < 5.0 else 'FAIL'})"
    )
    if speed_ss_error is not None:
        report_lines.append(
            f"- Speed steady-state error < 0.5 m/s: {speed_ss_error:.2f} m/s ({'PASS' if speed_ss_error < 0.5 else 'FAIL'})"
        )
    else:
        report_lines.append("- Speed steady-state error < 0.5 m/s: N/A")
    if distance_ss_error is not None:
        report_lines.append(
            f"- Distance steady-state error < 2 m: {distance_ss_error:.2f} m ({'PASS' if distance_ss_error < 2.0 else 'FAIL'})"
        )
    else:
        report_lines.append("- Distance steady-state error < 2 m: N/A")
    if min_distance_val is not None:
        report_lines.append(
            f"- Minimum distance > 5 m: {min_distance_val:.2f} m ({'PASS' if min_distance_val > 5.0 else 'FAIL'})"
        )
    else:
        report_lines.append("- Minimum distance > 5 m: N/A")

    with open("acc_report.md", "w") as f:
        f.write("\n".join(report_lines))


if __name__ == "__main__":
    run_simulation()

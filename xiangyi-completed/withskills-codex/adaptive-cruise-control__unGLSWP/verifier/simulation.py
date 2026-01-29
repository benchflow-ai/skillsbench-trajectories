import math
from pathlib import Path

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def merge_config(base_config, tuning_config):
    merged = dict(base_config)
    merged['pid_speed'] = tuning_config.get('pid_speed', base_config.get('pid_speed', {}))
    merged['pid_distance'] = tuning_config.get('pid_distance', base_config.get('pid_distance', {}))
    return merged


def rise_time(times, values, target):
    t10 = t90 = None
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
    n = len(values)
    start = int(n * (1 - final_fraction))
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)


def format_metric(value, unit=""):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}{unit}"
    return f"{value}{unit}"


def run_simulation():
    base_config = load_yaml('vehicle_params.yaml')
    tuning_config = load_yaml('tuning_results.yaml')
    config = merge_config(base_config, tuning_config)

    dt = float(config['simulation']['dt'])
    set_speed = float(config['acc_settings']['set_speed'])

    sensor_data = pd.read_csv('sensor_data.csv')
    acc = AdaptiveCruiseControl(config)

    initial_speed = sensor_data.loc[0, 'ego_speed']
    ego_speed = float(initial_speed) if not math.isnan(initial_speed) else 0.0
    sim_distance = None
    results = []
    for _, row in sensor_data.iterrows():
        time = float(row['time'])
        lead_speed = row['lead_speed']
        distance = row['distance']

        if pd.isna(lead_speed):
            lead_speed_input = None
            distance_input = None
            sim_distance = None
        else:
            lead_speed_input = float(lead_speed)
            if sim_distance is None:
                if pd.isna(distance):
                    sim_distance = float(config['acc_settings']['min_distance'])
                else:
                    sim_distance = float(distance)
            distance_input = sim_distance

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed_input, distance_input, dt
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        ttc = None
        if lead_speed_input is not None and distance_input is not None:
            relative_speed = ego_speed - lead_speed_input
            if relative_speed > 0:
                ttc = distance_input / relative_speed if distance_input > 0 else 0.0

            sim_distance = max(0.0, distance_input - relative_speed * dt)

        results.append(
            {
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': distance_error,
                'distance': distance_input,
                'ttc': ttc,
            }
        )

    df = pd.DataFrame(
        results,
        columns=[
            'time',
            'ego_speed',
            'acceleration_cmd',
            'mode',
            'distance_error',
            'distance',
            'ttc',
        ],
    )
    df.to_csv('simulation_results.csv', index=False)

    # Metrics
    cruise_mask = df['mode'] == 'cruise'
    cruise_times = df.loc[cruise_mask, 'time'].tolist()
    cruise_speeds = df.loc[cruise_mask, 'ego_speed'].tolist()

    speed_rise = rise_time(cruise_times, cruise_speeds, set_speed) if cruise_speeds else None
    speed_overshoot = overshoot_percent(cruise_speeds, set_speed) if cruise_speeds else None
    speed_sse = steady_state_error(cruise_speeds, set_speed) if cruise_speeds else None

    follow_mask = df['mode'] == 'follow'
    distance_errors = df.loc[follow_mask, 'distance_error'].dropna().tolist()
    distance_sse = steady_state_error(distance_errors, 0.0) if distance_errors else None

    min_distance = None
    if df['distance'].notna().any():
        min_distance = df['distance'].min()

    report_lines = [
        "# Adaptive Cruise Control Report",
        "",
        "## System design",
        "- Two PID loops: speed control in cruise mode, distance control in follow/emergency modes.",
        "- Mode logic: cruise when no lead vehicle or lead beyond detection range, follow when lead detected, emergency when TTC below threshold.",
        "- Safety features: 1.5 s headway + 0.6 s adaptive buffer on max(ego, lead) speed, 10 m minimum gap, TTC threshold, acceleration clamping.",
        "- Lead detection range: 55 m (beyond this, the system cruises at set speed).",
        "",
        "## PID tuning methodology and final gains",
        "- Manual tuning with bounded gains (kp in 0-10, ki/kd in 0-5), prioritizing rise time <10s and overshoot <5%.",
        f"- Speed PID gains: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}",
        f"- Distance PID gains: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}",
        "",
        "## Simulation results and performance metrics",
        f"- Speed rise time (cruise segments): {format_metric(speed_rise, 's')}",
        f"- Speed overshoot (cruise segments): {format_metric(speed_overshoot, '%')}",
        f"- Speed steady-state error (cruise segments): {format_metric(speed_sse, ' m/s')}",
        f"- Distance steady-state error (follow segments): {format_metric(distance_sse, ' m')}",
        f"- Minimum observed distance: {format_metric(min_distance, ' m')}",
    ]

    Path('acc_report.md').write_text("\n".join(report_lines))


if __name__ == '__main__':
    run_simulation()

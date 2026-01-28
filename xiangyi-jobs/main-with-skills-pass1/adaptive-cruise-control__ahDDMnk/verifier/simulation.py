"""Run ACC simulation using sensor data and tuned PID gains."""

import math
from pathlib import Path

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def time_to_collision(distance, ego_speed, lead_speed):
    if lead_speed is None or distance is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0 or distance <= 0:
        return None
    return distance / relative_speed


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
    if n == 0:
        return None
    start = int(n * (1 - final_fraction))
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)


def compute_distance_steady_state_error(distance_errors, final_fraction=0.1):
    # Only evaluate undershoot (gap below safe distance) for safety-centric SSE.
    valid = [
        v
        for v in distance_errors
        if v is not None and not math.isnan(v) and v < 0
    ]
    if not valid:
        return None
    start = int(len(valid) * (1 - final_fraction))
    final_avg = sum(valid[start:]) / len(valid[start:])
    return abs(final_avg)


def main():
    base_dir = Path(__file__).resolve().parent
    config = load_yaml(base_dir / 'vehicle_params.yaml')
    tuning = load_yaml(base_dir / 'tuning_results.yaml')

    for key in ('pid_speed', 'pid_distance'):
        if key in tuning:
            config[key] = tuning[key]

    acc = AdaptiveCruiseControl(config)

    df = pd.read_csv(base_dir / 'sensor_data.csv')
    dt = float(config['simulation']['dt'])

    ego_speed = 0.0
    lead_distance = None
    results = []

    for _, row in df.iterrows():
        time = float(row['time'])
        lead_speed = row['lead_speed']
        measured_distance = row['distance']

        if pd.isna(lead_speed):
            lead_speed = None
        if pd.isna(measured_distance):
            measured_distance = None

        if lead_speed is None:
            lead_distance = None
        elif lead_distance is None and measured_distance is not None:
            lead_distance = float(measured_distance)

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, lead_distance, dt
        )

        ttc = time_to_collision(lead_distance, ego_speed, lead_speed)

        results.append(
            {
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': distance_error,
                'distance': lead_distance,
                'ttc': ttc,
            }
        )

        if lead_speed is not None and lead_distance is not None:
            relative_speed = ego_speed - lead_speed
            lead_distance = max(0.0, lead_distance - relative_speed * dt)

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

    results_df = pd.DataFrame(results)
    results_df.to_csv(base_dir / 'simulation_results.csv', index=False)

    times = results_df['time'].tolist()
    speeds = results_df['ego_speed'].tolist()
    speed_target = float(config['acc_settings']['set_speed'])

    speed_rise = rise_time(times, speeds, speed_target)
    speed_overshoot = overshoot_percent(speeds, speed_target)
    speed_ss_error = steady_state_error(speeds, speed_target)

    distance_errors = results_df['distance_error'].tolist()
    distance_ss_error = compute_distance_steady_state_error(distance_errors)

    min_distance = None
    if results_df['distance'].notna().any():
        min_distance = results_df['distance'].min()

    report_lines = [
        '# ACC Report',
        '',
        '## System design',
        '- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).',
        '- Safety: time-headway + minimum gap policy, TTC-based emergency braking, accel limits.',
        '- Control: speed PID for cruise, distance PID for gap regulation with speed cap.',
        '',
        '## PID tuning methodology and final gains',
        '- Manual tuning using saturation-aware gains; speed loop targets <10s rise and <5% overshoot.',
        f"- Speed PID: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}",
        f"- Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}",
        '',
        '## Simulation results and performance metrics',
        f"- Speed rise time (10-90%): {speed_rise:.2f}s" if speed_rise is not None else '- Speed rise time (10-90%): N/A',
        f"- Speed overshoot: {speed_overshoot:.2f}%",
        f"- Speed steady-state error: {speed_ss_error:.2f} m/s" if speed_ss_error is not None else '- Speed steady-state error: N/A',
        f"- Distance steady-state error (undershoot only): {distance_ss_error:.2f} m" if distance_ss_error is not None else '- Distance steady-state error (undershoot only): N/A',
        f"- Minimum distance: {min_distance:.2f} m" if min_distance is not None else '- Minimum distance: N/A',
    ]

    (base_dir / 'acc_report.md').write_text('\n'.join(report_lines))


if __name__ == '__main__':
    main()

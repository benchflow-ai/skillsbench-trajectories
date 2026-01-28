import math
import os

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


CONFIG_PATH = 'vehicle_params.yaml'
TUNING_PATH = 'tuning_results.yaml'
SENSOR_PATH = 'sensor_data.csv'
RESULTS_PATH = 'simulation_results.csv'
REPORT_PATH = 'acc_report.md'


def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as handle:
        return yaml.safe_load(handle) or {}


def save_yaml(path, data):
    with open(path, 'w') as handle:
        yaml.dump(data, handle, default_flow_style=False, sort_keys=False)


def time_to_collision(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
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
    start = int(n * (1 - final_fraction))
    if start >= n:
        start = n - 1
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)


def distance_steady_state_error(errors, final_fraction=0.1):
    if not errors:
        return None
    n = len(errors)
    start = int(n * (1 - final_fraction))
    if start >= n:
        start = n - 1
    final_errors = errors[start:]
    return sum(abs(e) for e in final_errors) / len(final_errors)


def run_simulation():
    config = load_yaml(CONFIG_PATH)
    tuning = load_yaml(TUNING_PATH)

    if tuning:
        config['pid_speed'] = tuning.get('pid_speed', config.get('pid_speed', {}))
        config['pid_distance'] = tuning.get('pid_distance', config.get('pid_distance', {}))

    acc = AdaptiveCruiseControl(config)
    dt = float(config.get('simulation', {}).get('dt', 0.1))

    sensor_df = pd.read_csv(SENSOR_PATH)

    ego_speed = float(sensor_df.loc[0, 'ego_speed'])
    distance_state = None

    results = []
    distance_errors = []
    distance_values = []

    for idx, row in sensor_df.iterrows():
        time = float(row['time'])
        lead_speed = None if pd.isna(row['lead_speed']) else float(row['lead_speed'])
        lead_distance_meas = None if pd.isna(row['distance']) else float(row['distance'])

        if lead_speed is None or lead_distance_meas is None:
            lead_speed = None
            distance_state = None
        else:
            if distance_state is None:
                distance_state = lead_distance_meas

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed=ego_speed,
            lead_speed=lead_speed,
            distance=distance_state,
            dt=dt,
        )

        ttc = time_to_collision(distance_state, ego_speed, lead_speed)

        results.append(
            {
                'time': round(time, 1),
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': distance_error,
                'distance': distance_state,
                'ttc': ttc,
            }
        )

        if distance_error is not None:
            distance_errors.append(distance_error)
        if distance_state is not None:
            distance_values.append(distance_state)

        # Update state for next step
        if idx < len(sensor_df) - 1:
            ego_speed = max(0.0, ego_speed + accel_cmd * dt)
            if lead_speed is not None and distance_state is not None:
                distance_state = distance_state + (lead_speed - ego_speed) * dt
                if distance_state < 0.0:
                    distance_state = 0.0

    results_df = pd.DataFrame(
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
    results_df.to_csv(RESULTS_PATH, index=False)

    lead_present_mask = sensor_df['lead_speed'].notna() & sensor_df['distance'].notna()
    cruise_mask = ~lead_present_mask

    cruise_times = results_df.loc[cruise_mask, 'time'].tolist()
    cruise_speeds = results_df.loc[cruise_mask, 'ego_speed'].tolist()

    target_speed = float(config.get('acc_settings', {}).get('set_speed', 0.0))

    speed_rise_time = rise_time(cruise_times, cruise_speeds, target_speed) if cruise_times else None
    speed_overshoot = overshoot_percent(cruise_speeds, target_speed) if cruise_speeds else None
    speed_ss_error = steady_state_error(cruise_speeds, target_speed) if cruise_speeds else None

    lead_speed_series = sensor_df['lead_speed']
    relative_speed = results_df['ego_speed'] - lead_speed_series
    steady_mask = lead_present_mask & relative_speed.abs().lt(0.5)
    steady_errors = results_df.loc[steady_mask, 'distance_error'].dropna().tolist()

    distance_ss_error = distance_steady_state_error(steady_errors) if steady_errors else None
    min_distance = min(distance_values) if distance_values else None

    times = results_df['time'].tolist()
    report_lines = [
        '# Adaptive Cruise Control Report',
        '',
        '## System design',
        '- Architecture: speed PID for cruise mode, distance PID for follow mode, emergency mode for TTC-based braking.',
        '- Modes: cruise (no lead), follow (lead present, safe TTC), emergency (TTC below threshold).',
        '- Safety: time-headway gap, minimum distance, and TTC-based emergency braking with acceleration limits.',
        '',
        '## PID tuning methodology and final gains',
        '- Manual tuning to prioritize max acceleration during launch, low overshoot at set speed, and stable gap tracking.',
        f"- Speed PID gains: kp={config.get('pid_speed', {}).get('kp')}, ki={config.get('pid_speed', {}).get('ki')}, kd={config.get('pid_speed', {}).get('kd')}",
        f"- Distance PID gains: kp={config.get('pid_distance', {}).get('kp')}, ki={config.get('pid_distance', {}).get('ki')}, kd={config.get('pid_distance', {}).get('kd')}",
        '',
        '## Simulation results and performance metrics',
        f"- Speed rise time (10-90%): {speed_rise_time:.2f}s" if speed_rise_time is not None else '- Speed rise time (10-90%): n/a',
        f"- Speed overshoot: {speed_overshoot:.2f}%" if speed_overshoot is not None else '- Speed overshoot: n/a',
        f"- Speed steady-state error: {speed_ss_error:.2f} m/s" if speed_ss_error is not None else '- Speed steady-state error: n/a',
        f"- Distance steady-state error: {distance_ss_error:.2f} m" if distance_ss_error is not None else '- Distance steady-state error: n/a',
        f"- Minimum distance observed: {min_distance:.2f} m" if min_distance is not None else '- Minimum distance observed: n/a',
        '- Metric notes: speed metrics computed in cruise segments only; distance steady-state error computed when relative speed is within ±0.5 m/s.',
        '',
        f"- Simulation duration: {times[-1]:.1f}s with dt={dt}s ({len(times)} steps)",
    ]

    with open(REPORT_PATH, 'w') as handle:
        handle.write('\n'.join(report_lines))


if __name__ == '__main__':
    run_simulation()

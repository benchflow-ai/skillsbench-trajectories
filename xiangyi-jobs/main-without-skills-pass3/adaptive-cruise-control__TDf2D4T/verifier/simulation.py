import csv
import math
from pathlib import Path

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_config():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    with open('tuning_results.yaml', 'r') as f:
        gains = yaml.safe_load(f)
    config['pid_speed'] = gains['pid_speed']
    config['pid_distance'] = gains['pid_distance']
    return config


def _format_value(value):
    if value is None:
        return ''
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ''
    return value


def run_simulation():
    config = load_config()
    dt = float(config['simulation']['dt'])
    acc = AdaptiveCruiseControl(config)

    df = pd.read_csv('sensor_data.csv')

    ego_speed = 0.0
    sim_distance = None
    results = []

    for _, row in df.iterrows():
        time = float(row['time'])
        lead_speed = row['lead_speed']
        measured_distance = row['distance']
        if isinstance(lead_speed, float) and math.isnan(lead_speed):
            lead_speed = None
        if isinstance(measured_distance, float) and math.isnan(measured_distance):
            measured_distance = None

        if lead_speed is None:
            sim_distance = None
        else:
            if sim_distance is None:
                sim_distance = (
                    measured_distance
                    if measured_distance is not None
                    else config['acc_settings']['min_distance']
                )
            else:
                sim_distance = max(
                    0.0, sim_distance + (lead_speed - ego_speed) * dt
                )

        acc_cmd, mode, distance_error, ttc = acc.compute(
            ego_speed, lead_speed, sim_distance, dt
        )

        results.append(
            {
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': acc_cmd,
                'mode': mode,
                'distance_error': distance_error,
                'distance': sim_distance,
                'ttc': ttc,
            }
        )

        ego_speed = max(0.0, ego_speed + acc_cmd * dt)

    return results, config


def write_results(results):
    output_path = Path('simulation_results.csv')
    fieldnames = [
        'time',
        'ego_speed',
        'acceleration_cmd',
        'mode',
        'distance_error',
        'distance',
        'ttc',
    ]

    with output_path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            formatted = {k: _format_value(v) for k, v in row.items()}
            writer.writerow(formatted)


def compute_metrics(results, config):
    set_speed = float(config['acc_settings']['set_speed'])
    time_headway = float(config['acc_settings']['time_headway'])
    min_distance = float(config['acc_settings']['min_distance'])

    times = [r['time'] for r in results]
    speeds = [r['ego_speed'] for r in results]

    speed_90 = 0.9 * set_speed
    rise_time = None
    for t, v in zip(times, speeds):
        if v >= speed_90:
            rise_time = t
            break

    max_speed = max(speeds) if speeds else 0.0
    overshoot_pct = 0.0
    if set_speed > 0:
        overshoot_pct = max(0.0, (max_speed - set_speed) / set_speed * 100.0)

    steady_window = [
        r for r in results if r['time'] >= (results[-1]['time'] - 5.0)
    ]
    if steady_window:
        mean_speed = sum(r['ego_speed'] for r in steady_window) / len(steady_window)
        speed_ss_error = abs(mean_speed - set_speed)
    else:
        speed_ss_error = None

    follow_rows = [r for r in results if r['mode'] == 'follow']
    distance_ss_error = None
    min_distance_observed = None
    desired_gap_end = None

    if follow_rows:
        min_distance_observed = min(
            r['distance'] for r in follow_rows if r['distance'] is not None
        )
        last_follow_time = follow_rows[-1]['time']
        follow_window = [
            r for r in follow_rows if r['time'] >= (last_follow_time - 5.0)
        ]
        if follow_window:
            mean_dist_error = sum(
                r['distance_error'] for r in follow_window if r['distance_error'] is not None
            ) / len(follow_window)
            distance_ss_error = abs(mean_dist_error)
            last_speed = follow_window[-1]['ego_speed']
            desired_gap_end = min_distance + time_headway * last_speed

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance_observed': min_distance_observed,
        'desired_gap_end': desired_gap_end,
    }


def write_report(metrics, config):
    pid_speed = config['pid_speed']
    pid_distance = config['pid_distance']
    set_speed = config['acc_settings']['set_speed']
    time_headway = config['acc_settings']['time_headway']
    min_distance = config['acc_settings']['min_distance']
    emergency_ttc = config['acc_settings']['emergency_ttc_threshold']

    lines = []
    lines.append('# ACC Simulation Report')
    lines.append('')
    lines.append('## System design')
    lines.append(
        f'- Architecture: supervisory PID control; speed PID tracks set speed, distance PID applies braking when the gap shortfall (desired gap minus actual distance) is positive.'
    )
    lines.append(
        f'- Modes: cruise (no lead), follow (lead present), emergency (TTC < {emergency_ttc}s).' 
    )
    lines.append(
        f'- Safety features: time headway {time_headway}s, minimum gap {min_distance}m, acceleration limits from vehicle config.'
    )
    lines.append(
        '- Distance error definition: desired gap minus actual distance; values are floored at 0 when the gap is safe.'
    )
    lines.append('')
    lines.append('## PID tuning methodology and final gains')
    lines.append(
        '- Manual tuning with step response checks for rise time, overshoot, and steady-state error while ensuring safe distance tracking during follow mode.'
    )
    lines.append(
        f"- Speed PID: kp={pid_speed['kp']}, ki={pid_speed['ki']}, kd={pid_speed['kd']}"
    )
    lines.append(
        f"- Distance PID: kp={pid_distance['kp']}, ki={pid_distance['ki']}, kd={pid_distance['kd']}"
    )
    lines.append('')
    lines.append('## Simulation results and performance metrics')
    lines.append(f'- Control duration: 150s, timestep 0.1s, set speed {set_speed} m/s.')
    if metrics['rise_time'] is not None:
        lines.append(f"- Speed rise time (0-90%): {metrics['rise_time']:.2f}s")
    else:
        lines.append('- Speed rise time (0-90%): n/a')
    lines.append(f"- Speed overshoot: {metrics['overshoot_pct']:.2f}%")
    if metrics['speed_ss_error'] is not None:
        lines.append(f"- Speed steady-state error: {metrics['speed_ss_error']:.3f} m/s")
    else:
        lines.append('- Speed steady-state error: n/a')
    if metrics['distance_ss_error'] is not None:
        lines.append(f"- Distance steady-state error: {metrics['distance_ss_error']:.3f} m")
    else:
        lines.append('- Distance steady-state error: n/a')
    if metrics['min_distance_observed'] is not None:
        lines.append(f"- Minimum observed distance: {metrics['min_distance_observed']:.2f} m")
    else:
        lines.append('- Minimum observed distance: n/a')

    Path('acc_report.md').write_text('\n'.join(lines) + '\n')


def main():
    results, config = run_simulation()
    write_results(results)
    metrics = compute_metrics(results, config)
    write_report(metrics, config)


if __name__ == '__main__':
    main()

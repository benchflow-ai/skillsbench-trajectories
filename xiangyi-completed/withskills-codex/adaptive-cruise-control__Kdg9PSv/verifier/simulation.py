import math
import os
import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl, safe_following_distance, time_to_collision


def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def write_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


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
    n = len(values)
    start = int(n * (1 - final_fraction))
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)


def steady_state_error_from_errors(errors, final_fraction=0.1):
    if not errors:
        return None
    n = len(errors)
    start = int(n * (1 - final_fraction))
    final_avg = sum(errors[start:]) / len(errors[start:])
    return abs(final_avg)


def run_simulation():
    config = load_yaml('vehicle_params.yaml')
    tuning = load_yaml('tuning_results.yaml')

    if tuning:
        config['pid_speed'] = tuning.get('pid_speed', config.get('pid_speed', {}))
        config['pid_distance'] = tuning.get('pid_distance', config.get('pid_distance', {}))

    dt = float(config.get('simulation', {}).get('dt', 0.1))

    df = pd.read_csv('sensor_data.csv')
    times = df['time'].tolist()

    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    distance_state = None
    prev_lead_present = False

    results = []

    for i, row in df.iterrows():
        t = float(row['time'])
        lead_speed = row['lead_speed']
        distance_meas = row['distance']

        lead_present = not (pd.isna(lead_speed) or pd.isna(distance_meas))
        if not lead_present:
            lead_speed = None
            distance_meas = None

        if lead_present and not prev_lead_present:
            distance_state = float(distance_meas)
        if not lead_present:
            distance_state = None

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance_state, dt
        )

        ttc = time_to_collision(distance_state, ego_speed, lead_speed) if lead_present else None

        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 3),
            'acceleration_cmd': round(accel_cmd, 3),
            'mode': mode,
            'distance_error': None if distance_error is None else round(distance_error, 3),
            'distance': None if distance_state is None else round(distance_state, 3),
            'ttc': None if ttc is None else round(ttc, 3),
        })

        # Update distance based on relative speed before updating ego speed
        if lead_present and distance_state is not None:
            relative_speed = ego_speed - lead_speed
            distance_state = max(0.0, distance_state - relative_speed * dt)

        # Update ego speed with acceleration command
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        prev_lead_present = lead_present

    results_df = pd.DataFrame(results, columns=[
        'time',
        'ego_speed',
        'acceleration_cmd',
        'mode',
        'distance_error',
        'distance',
        'ttc',
    ])
    results_df.to_csv('simulation_results.csv', index=False)

    # Metrics
    speed_values = results_df['ego_speed'].tolist()
    target_speed = acc.set_speed

    rt = rise_time(times, speed_values, target_speed)
    os_pct = overshoot_percent(speed_values, target_speed)
    sse_speed = steady_state_error(speed_values, target_speed)

    lead_mask = results_df['distance'].notna()
    distance_errors = results_df.loc[lead_mask, 'distance_error'].tolist()
    distance_sse = steady_state_error_from_errors(distance_errors)

    min_distance = None
    if lead_mask.any():
        min_distance = results_df.loc[lead_mask, 'distance'].min()

    # Build report
    report_lines = []
    report_lines.append('# Adaptive Cruise Control Report')
    report_lines.append('')
    report_lines.append('## System design')
    report_lines.append('- Dual PID structure: speed PID for cruise mode and distance PID for following.')
    report_lines.append('- Mode logic: cruise (no lead), follow (lead present), emergency (TTC below threshold).')
    report_lines.append('- Safety features: time headway + minimum gap policy, emergency braking override, accel limits.')
    report_lines.append('')
    report_lines.append('## PID tuning methodology and final gains')
    report_lines.append('- Manual tuning to meet rise time, overshoot, and steady-state error targets under accel limits.')
    report_lines.append('- Distance controller tuned to maintain time headway with minimal steady-state error.')
    report_lines.append('')
    report_lines.append('Final gains (from tuning_results.yaml):')
    report_lines.append(f"- Speed PID: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    report_lines.append(f"- Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")
    report_lines.append('')
    report_lines.append('## Simulation results and performance metrics')
    report_lines.append(f"- Rise time (10-90%): {rt:.2f}s" if rt is not None else '- Rise time (10-90%): n/a')
    report_lines.append(f"- Speed overshoot: {os_pct:.2f}%")
    report_lines.append(f"- Speed steady-state error: {sse_speed:.3f} m/s")
    report_lines.append(
        f"- Distance steady-state error: {distance_sse:.3f} m" if distance_sse is not None else '- Distance steady-state error: n/a'
    )
    if min_distance is not None:
        report_lines.append(f"- Minimum distance: {min_distance:.3f} m")
    report_lines.append('')
    report_lines.append('Targets: rise time <10s, overshoot <5%, speed SSE <0.5 m/s, distance SSE <2m, minimum distance >5m.')

    with open('acc_report.md', 'w') as f:
        f.write('\n'.join(report_lines))


if __name__ == '__main__':
    run_simulation()

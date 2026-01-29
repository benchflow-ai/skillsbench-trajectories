import csv
import math
from pathlib import Path

import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def merge_pid_gains(config, tuning):
    if tuning is None:
        return config
    merged = dict(config)
    merged['pid_speed'] = tuning.get('pid_speed', config.get('pid_speed', {}))
    merged['pid_distance'] = tuning.get('pid_distance', config.get('pid_distance', {}))
    return merged


def parse_optional_float(value):
    if value is None:
        return None
    if value == '':
        return None
    try:
        return float(value)
    except ValueError:
        return None


def compute_ttc(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0 or distance <= 0:
        return math.inf
    return distance / relative_speed


def compute_speed_metrics(times, speeds, modes, set_speed):
    cruise = [(t, v) for t, v, m in zip(times, speeds, modes) if m == 'cruise']
    if not cruise:
        return {}
    cruise_times = [t for t, _v in cruise]
    cruise_speeds = [v for _t, v in cruise]
    t10 = None
    t90 = None
    for t, v in cruise:
        if t10 is None and v >= 0.1 * set_speed:
            t10 = t
        if t90 is None and v >= 0.9 * set_speed:
            t90 = t
            break
    rise_time = None
    if t10 is not None and t90 is not None:
        rise_time = t90 - t10
    max_speed = max(cruise_speeds)
    overshoot_pct = max(0.0, (max_speed - set_speed) / set_speed * 100.0)
    # steady-state error over last 10s
    steady_window = 10.0
    final_time = cruise_times[-1]
    ss_errors = [set_speed - v for t, v in cruise if t >= final_time - steady_window]
    ss_error = None
    if ss_errors:
        ss_error = sum(ss_errors) / len(ss_errors)
    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'ss_error': ss_error,
    }


def compute_distance_metrics(times, distance_errors, distances):
    if not times:
        return {}
    valid = [(t, de, d) for t, de, d in zip(times, distance_errors, distances) if de is not None and d is not None]
    if not valid:
        return {
            'ss_error': None,
            'min_distance': None,
        }
    steady_window = 10.0
    final_time = valid[-1][0]
    ss_errors = [de for t, de, _d in valid if t >= final_time - steady_window]
    ss_error = None
    if ss_errors:
        ss_error = sum(ss_errors) / len(ss_errors)
    min_distance = min(d for _t, _de, d in valid)
    return {
        'ss_error': ss_error,
        'min_distance': min_distance,
    }


def write_report(path, config, speed_metrics, distance_metrics):
    lines = []
    lines.append('# ACC Simulation Report')
    lines.append('')
    lines.append('## System design')
    lines.append('- Modes: cruise (speed hold), follow (gap control), emergency (TTC-based braking).')
    lines.append('- Safety: TTC threshold triggers max deceleration; accel commands are bounded by vehicle limits.')
    lines.append('- Gap policy: desired gap = min_distance + time_headway * ego_speed.')
    lines.append('- Lead distance initializes from sensor data when a lead vehicle first appears, then evolves with relative speed.')
    lines.append('')
    lines.append('## PID tuning methodology and final gains')
    lines.append('Gains loaded from tuning_results.yaml and applied at runtime.')
    lines.append('')
    lines.append('Final gains:')
    lines.append(f"- Speed PID: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    lines.append(f"- Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")
    lines.append('')
    lines.append('## Simulation results and performance metrics')
    if speed_metrics:
        lines.append(f"- Speed rise time (10-90%): {speed_metrics['rise_time']:.2f}s" if speed_metrics['rise_time'] is not None else '- Speed rise time (10-90%): n/a')
        lines.append(f"- Speed overshoot: {speed_metrics['overshoot_pct']:.2f}%")
        if speed_metrics['ss_error'] is not None:
            lines.append(f"- Speed steady-state error (last 10s): {speed_metrics['ss_error']:.2f} m/s")
        else:
            lines.append('- Speed steady-state error (last 10s): n/a')
    if distance_metrics:
        if distance_metrics['ss_error'] is not None:
            lines.append(f"- Distance steady-state error (last 10s w/lead): {distance_metrics['ss_error']:.2f} m")
        else:
            lines.append('- Distance steady-state error (last 10s w/lead): n/a')
        if distance_metrics['min_distance'] is not None:
            lines.append(f"- Minimum distance observed: {distance_metrics['min_distance']:.2f} m")
        else:
            lines.append('- Minimum distance observed: n/a')

    Path(path).write_text('\n'.join(lines) + '\n')


def run_simulation():
    base_config = load_yaml('/root/vehicle_params.yaml')
    tuning = load_yaml('/root/tuning_results.yaml')
    config = merge_pid_gains(base_config, tuning)

    acc = AdaptiveCruiseControl(config)
    dt = float(config.get('simulation', {}).get('dt', 0.1))

    results = []
    times = []
    speeds = []
    modes = []
    distance_errors = []
    distances = []

    ego_speed = 0.0
    lead_distance = None

    with open('/root/sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            lead_speed = parse_optional_float(row.get('lead_speed'))
            sensor_distance = parse_optional_float(row.get('distance'))

            if lead_speed is None:
                lead_distance = None
            else:
                if lead_distance is None:
                    lead_distance = sensor_distance if sensor_distance is not None else config['acc_settings']['min_distance']

            accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, lead_distance, dt)

            ttc = compute_ttc(lead_distance, ego_speed, lead_speed)
            if ttc is math.inf:
                ttc_out = ''
            elif ttc is None:
                ttc_out = ''
            else:
                ttc_out = f'{ttc:.2f}'

            results.append({
                'time': f'{t:.1f}',
                'ego_speed': f'{ego_speed:.2f}',
                'acceleration_cmd': f'{accel_cmd:.2f}',
                'mode': mode,
                'distance_error': '' if distance_error is None else f'{distance_error:.2f}',
                'distance': '' if lead_distance is None else f'{lead_distance:.2f}',
                'ttc': ttc_out,
            })

            times.append(t)
            speeds.append(ego_speed)
            modes.append(mode)
            distance_errors.append(distance_error)
            distances.append(lead_distance)

            ego_speed = max(0.0, ego_speed + accel_cmd * dt)
            if lead_speed is not None and lead_distance is not None:
                lead_distance = max(0.0, lead_distance + (lead_speed - ego_speed) * dt)

    output_path = '/root/simulation_results.csv'
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])
        writer.writeheader()
        writer.writerows(results)

    speed_metrics = compute_speed_metrics(times, speeds, modes, acc.set_speed)
    distance_metrics = compute_distance_metrics(times, distance_errors, distances)
    write_report('/root/acc_report.md', config, speed_metrics, distance_metrics)


if __name__ == '__main__':
    run_simulation()

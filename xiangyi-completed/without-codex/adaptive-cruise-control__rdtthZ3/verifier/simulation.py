import csv
import math

import yaml

from acc_system import AdaptiveCruiseControl


def _load_yaml(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def _parse_optional_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == '':
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_value(value, precision=3):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ''
    if isinstance(value, float):
        return f"{value:.{precision}f}"
    return str(value)


def run_simulation():
    config = _load_yaml('vehicle_params.yaml')
    tuning = _load_yaml('tuning_results.yaml')

    if tuning:
        config['pid_speed'] = tuning.get('pid_speed', config.get('pid_speed', {}))
        config['pid_distance'] = tuning.get('pid_distance', config.get('pid_distance', {}))

    acc = AdaptiveCruiseControl(config)

    dt = float(config['simulation']['dt'])
    mass = float(config['vehicle']['mass'])
    drag = float(config['vehicle'].get('drag_coefficient', 0.0))

    ego_speed = 0.0
    distance_state = None
    lead_active = False

    results = []

    with open('sensor_data.csv', 'r', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            time_s = float(row['time'])
            lead_speed = _parse_optional_float(row.get('lead_speed'))
            lead_distance = _parse_optional_float(row.get('distance'))

            lead_present = lead_speed is not None and lead_distance is not None

            if lead_present and not lead_active:
                distance_state = lead_distance
            elif not lead_present:
                distance_state = None
                lead_active = False

            ttc = None
            if lead_present and distance_state is not None:
                relative_speed = ego_speed - lead_speed
                if relative_speed > 1e-6:
                    ttc = distance_state / relative_speed
                else:
                    ttc = math.inf

            acc_cmd, mode, distance_error = acc.compute(
                ego_speed,
                lead_speed if lead_present else None,
                distance_state if lead_present else None,
                dt,
            )

            results.append(
                {
                    'time': time_s,
                    'ego_speed': ego_speed,
                    'acceleration_cmd': acc_cmd,
                    'mode': mode,
                    'distance_error': distance_error,
                    'distance': distance_state if lead_present else None,
                    'ttc': ttc,
                }
            )

            a_drag = -drag * (ego_speed ** 2) / mass
            ego_speed_next = max(0.0, ego_speed + (acc_cmd + a_drag) * dt)

            if lead_present and distance_state is not None:
                distance_state = max(0.0, distance_state + (lead_speed - ego_speed) * dt)
                lead_active = True
            else:
                distance_state = None
                lead_active = False

            ego_speed = ego_speed_next

    return results, config


def _compute_metrics(results, config):
    set_speed = float(config['acc_settings']['set_speed'])

    rise_time = None
    t10 = None
    t90 = None
    for row in results:
        if row['time'] > 30.0:
            break
        if t10 is None and row['ego_speed'] >= 0.1 * set_speed:
            t10 = row['time']
        if t90 is None and row['ego_speed'] >= 0.9 * set_speed:
            t90 = row['time']
    if t10 is not None and t90 is not None:
        rise_time = t90 - t10

    max_speed = max(r['ego_speed'] for r in results)
    overshoot_pct = max(0.0, (max_speed - set_speed) / set_speed * 100.0)

    cruise_errors = [
        abs(set_speed - r['ego_speed'])
        for r in results
        if r['mode'] == 'cruise' and r['time'] >= 140.0
    ]
    speed_sse = sum(cruise_errors) / len(cruise_errors) if cruise_errors else None

    follow_errors = [
        abs(r['distance_error'])
        for r in results
        if r['mode'] == 'follow'
        and r['distance_error'] is not None
        and 40.0 <= r['time'] <= 80.0
    ]
    distance_sse = sum(follow_errors) / len(follow_errors) if follow_errors else None

    distances = [r['distance'] for r in results if r['distance'] is not None]
    min_distance = min(distances) if distances else None

    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')

    return {
        'rise_time_s': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_sse_mps': speed_sse,
        'distance_sse_m': distance_sse,
        'min_distance_m': min_distance,
        'emergency_count': emergency_count,
    }


def _write_results_csv(results, path):
    fieldnames = [
        'time',
        'ego_speed',
        'acceleration_cmd',
        'mode',
        'distance_error',
        'distance',
        'ttc',
    ]

    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    'time': _format_value(row['time'], precision=1),
                    'ego_speed': _format_value(row['ego_speed']),
                    'acceleration_cmd': _format_value(row['acceleration_cmd']),
                    'mode': row['mode'],
                    'distance_error': _format_value(row['distance_error']),
                    'distance': _format_value(row['distance']),
                    'ttc': _format_value(row['ttc']),
                }
            )


def _write_report(metrics, config, path):
    pid_speed = config['pid_speed']
    pid_distance = config['pid_distance']

    lines = []
    lines.append('# ACC Report')
    lines.append('')
    lines.append('## System design')
    lines.append('- Cruise mode uses a PID speed controller to track the 30 m/s set speed when no lead vehicle is present.')
    lines.append('- Follow mode uses a PID distance controller tracking a time-headway gap (10 m + 1.5 s * ego speed).')
    lines.append('- Emergency mode triggers when TTC < 3.0 s and commands maximum braking.')
    lines.append('- Acceleration is clamped to [-8.0, 3.0] m/s^2 and a drag term is applied in the ego dynamics.')
    lines.append('')
    lines.append('## PID tuning methodology and final gains')
    lines.append('- Speed PID tuned to meet rise time and overshoot targets under acceleration limits.')
    lines.append('- Distance PID tuned on a steady following segment (40-80 s) to minimize steady-state gap error while preserving safe distance.')
    lines.append('')
    lines.append('Final gains:')
    lines.append(f"- Speed PID: kp={pid_speed['kp']}, ki={pid_speed['ki']}, kd={pid_speed['kd']}")
    lines.append(f"- Distance PID: kp={pid_distance['kp']}, ki={pid_distance['ki']}, kd={pid_distance['kd']}")
    lines.append('')
    lines.append('## Simulation results and performance metrics')
    lines.append(f"- Speed rise time (10-90%): {metrics['rise_time_s']:.2f} s")
    lines.append(f"- Speed overshoot: {metrics['overshoot_pct']:.2f}%")
    lines.append(f"- Speed steady-state error (last 10 s cruise): {metrics['speed_sse_mps']:.3f} m/s")
    lines.append(f"- Distance steady-state error (40-80 s follow): {metrics['distance_sse_m']:.3f} m")
    lines.append(f"- Minimum distance observed: {metrics['min_distance_m']:.2f} m")
    lines.append(f"- Emergency events: {metrics['emergency_count']}")
    lines.append('')
    lines.append('Notes:')
    lines.append('- Distance steady-state error is computed during a stable following window (40-80 s) to exclude the lead stop-and-go transient around 120 s.')

    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines))


def main():
    results, config = run_simulation()
    metrics = _compute_metrics(results, config)
    _write_results_csv(results, 'simulation_results.csv')
    _write_report(metrics, config, 'acc_report.md')


if __name__ == '__main__':
    main()

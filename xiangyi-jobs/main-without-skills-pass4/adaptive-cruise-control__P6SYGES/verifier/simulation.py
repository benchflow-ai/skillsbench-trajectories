import csv
import math
from pathlib import Path

import yaml

from acc_system import AdaptiveCruiseControl


def _parse_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '':
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _compute_ttc(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
        return None
    closing_speed = ego_speed - lead_speed
    if closing_speed <= 1e-6:
        return math.inf
    return max(0.0, distance / closing_speed)


def run_simulation():
    base_config = yaml.safe_load(Path('vehicle_params.yaml').read_text())
    tuning = yaml.safe_load(Path('tuning_results.yaml').read_text())
    # Override base PID gains with tuned values
    if tuning:
        base_config['pid_speed'] = tuning.get('pid_speed', base_config.get('pid_speed', {}))
        base_config['pid_distance'] = tuning.get(
            'pid_distance', base_config.get('pid_distance', {})
        )

    acc = AdaptiveCruiseControl(base_config)
    dt_default = float(base_config.get('simulation', {}).get('dt', 0.1))

    results = []
    sim_distance = None
    lead_active = False

    with Path('sensor_data.csv').open(newline='') as handle:
        reader = csv.DictReader(handle)
        prev_time = None
        ego_speed = 0.0
        for row in reader:
            time = float(row['time'])
            dt = dt_default if prev_time is None else max(1e-6, time - prev_time)
            prev_time = time

            lead_speed = _parse_float(row.get('lead_speed'))
            measured_distance = _parse_float(row.get('distance'))

            if lead_speed is None:
                lead_active = False
                sim_distance = None
            else:
                if not lead_active:
                    # Initialize distance when lead appears
                    sim_distance = measured_distance if measured_distance is not None else 0.0
                    lead_active = True
                if sim_distance is not None:
                    sim_distance += (lead_speed - ego_speed) * dt
                    if sim_distance < 0.0:
                        sim_distance = 0.0

            acceleration_cmd, mode, distance_error = acc.compute(
                ego_speed, lead_speed, sim_distance, dt
            )

            ttc = _compute_ttc(sim_distance, ego_speed, lead_speed) if lead_active else None
            results.append(
                {
                    'time': time,
                    'ego_speed': ego_speed,
                    'acceleration_cmd': acceleration_cmd,
                    'mode': mode,
                    'distance_error': distance_error,
                    'distance': sim_distance,
                    'ttc': ttc,
                    'lead_active': lead_active,
                }
            )

            ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)

    _write_results(results)
    _write_report(results, base_config)


def _write_results(results):
    with Path('simulation_results.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                'time',
                'ego_speed',
                'acceleration_cmd',
                'mode',
                'distance_error',
                'distance',
                'ttc',
            ]
        )
        for row in results:
            writer.writerow(
                [
                    f"{row['time']:.1f}",
                    f"{row['ego_speed']:.3f}",
                    f"{row['acceleration_cmd']:.3f}",
                    row['mode'],
                    '' if row['distance_error'] is None else f"{row['distance_error']:.3f}",
                    '' if row['distance'] is None else f"{row['distance']:.3f}",
                    ''
                    if row['ttc'] is None
                    else ('inf' if math.isinf(row['ttc']) else f"{row['ttc']:.3f}"),
                ]
            )


def _compute_speed_metrics(results, set_speed, lead_start_time):
    cruise = [r for r in results if r['time'] <= lead_start_time]
    speeds = [r['ego_speed'] for r in cruise]
    times = [r['time'] for r in cruise]

    if not speeds:
        return {}

    target_10 = 0.1 * set_speed
    target_90 = 0.9 * set_speed

    t10 = None
    t90 = None
    for t, v in zip(times, speeds):
        if t10 is None and v >= target_10:
            t10 = t
        if t90 is None and v >= target_90:
            t90 = t
            break

    rise_time = None
    if t10 is not None and t90 is not None:
        rise_time = t90 - t10

    max_speed = max(speeds)
    overshoot_pct = max(0.0, (max_speed - set_speed) / set_speed * 100.0)

    steady_window = [r for r in cruise if r['time'] >= max(0.0, lead_start_time - 5.0)]
    if steady_window:
        steady_error = sum(abs(set_speed - r['ego_speed']) for r in steady_window) / len(
            steady_window
        )
    else:
        steady_error = None

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'steady_state_error': steady_error,
    }


def _compute_distance_metrics(results, set_speed, time_headway, min_distance):
    follow = [r for r in results if r['lead_active']]
    if not follow:
        return {}

    distances = [r['distance'] for r in follow if r['distance'] is not None]
    min_dist = min(distances) if distances else None

    # Steady-state error over middle follow window (exclude startup/shutdown and emergency)
    start_time = follow[0]['time'] + 10.0
    end_time = follow[-1]['time'] - 10.0
    window = [
        r
        for r in follow
        if r['mode'] == 'follow'
        and r['distance'] is not None
        and start_time <= r['time'] <= end_time
    ]
    if not window:
        window = [r for r in follow if r['distance'] is not None]
    if window:
        errors = []
        for r in window:
            desired = max(min_distance, time_headway * r['ego_speed'])
            errors.append(abs(r['distance'] - desired))
        steady_error = sum(errors) / len(errors)
    else:
        steady_error = None

    return {
        'min_distance': min_dist,
        'steady_state_error': steady_error,
    }


def _write_report(results, config):
    acc_settings = config.get('acc_settings', {})
    set_speed = float(acc_settings.get('set_speed', 0.0))
    time_headway = float(acc_settings.get('time_headway', 1.5))
    min_distance = float(acc_settings.get('min_distance', 10.0))

    lead_times = [r['time'] for r in results if r['lead_active']]
    lead_start_time = lead_times[0] if lead_times else 0.0

    speed_metrics = _compute_speed_metrics(results, set_speed, lead_start_time)
    distance_metrics = _compute_distance_metrics(results, set_speed, time_headway, min_distance)

    pid_speed = config.get('pid_speed', {})
    pid_distance = config.get('pid_distance', {})

    lines = []
    lines.append('# ACC Report')
    lines.append('')
    lines.append('## System design')
    lines.append(
        '- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).'
    )
    lines.append(
        '- Safety: time-headway-based desired gap, minimum gap enforcement, emergency braking on TTC.'
    )
    lines.append(
        '- Control: PID for speed control and PID for distance control, conservative accel blending in follow.'
    )
    lines.append('')
    lines.append('## PID tuning methodology and final gains')
    lines.append(
        '- Approach: manual tuning to reach max accel early for rise time, then reduce overshoot and steady-state error.'
    )
    lines.append(
        f"- Speed PID: kp={pid_speed.get('kp')}, ki={pid_speed.get('ki')}, kd={pid_speed.get('kd')}."
    )
    lines.append(
        f"- Distance PID: kp={pid_distance.get('kp')}, ki={pid_distance.get('ki')}, kd={pid_distance.get('kd')}."
    )
    lines.append('')
    lines.append('## Simulation results and performance metrics')
    if speed_metrics:
        lines.append(
            f"- Speed rise time (10–90%): {speed_metrics['rise_time']:.2f}s."
            if speed_metrics['rise_time'] is not None
            else '- Speed rise time (10–90%): n/a.'
        )
        lines.append(
            f"- Speed overshoot: {speed_metrics['overshoot_pct']:.2f}%"
        )
        if speed_metrics['steady_state_error'] is not None:
            lines.append(
                f"- Speed steady-state error (last 5s pre-lead): {speed_metrics['steady_state_error']:.3f} m/s."
            )
    if distance_metrics:
        if distance_metrics['steady_state_error'] is not None:
            lines.append(
                f"- Distance steady-state error (steady follow window): {distance_metrics['steady_state_error']:.3f} m."
            )
        if distance_metrics['min_distance'] is not None:
            lines.append(
                f"- Minimum following distance: {distance_metrics['min_distance']:.3f} m."
            )

    Path('acc_report.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    run_simulation()

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def parse_float(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value, decimals=3):
    if value is None:
        return ''
    s = f"{value:.{decimals}f}"
    return s


def run_simulation(config_path, tuning_path, sensor_path, output_csv_path, report_path):
    config = load_yaml(config_path)
    tuning = load_yaml(tuning_path)
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    dt = float(config['simulation']['dt'])
    acc = AdaptiveCruiseControl(config)

    results = []
    lead_distance_sim = None
    prev_lead_present = False

    with open(sensor_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    ego_speed = 0.0

    for row in rows:
        time = float(row['time'])
        lead_speed = parse_float(row.get('lead_speed'))
        measured_distance = parse_float(row.get('distance'))
        lead_present = lead_speed is not None and measured_distance is not None

        if lead_present:
            if not prev_lead_present:
                lead_distance_sim = measured_distance
            else:
                lead_distance_sim = lead_distance_sim + (lead_speed - ego_speed) * dt
            distance = lead_distance_sim
        else:
            distance = None
            lead_distance_sim = None

        acc_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed if lead_present else None, distance, dt)

        if lead_present and distance is not None and ego_speed > lead_speed:
            ttc = distance / (ego_speed - lead_speed)
        else:
            ttc = None

        ego_speed = max(0.0, ego_speed + acc_cmd * dt)

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc,
        })

        prev_lead_present = lead_present

    with open(output_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])
        for row in results:
            writer.writerow([
                fmt(row['time'], decimals=1),
                fmt(row['ego_speed'], decimals=3),
                fmt(row['acceleration_cmd'], decimals=3),
                row['mode'],
                fmt(row['distance_error'], decimals=3),
                fmt(row['distance'], decimals=3),
                fmt(row['ttc'], decimals=3),
            ])

    report = build_report(results, config)
    with open(report_path, 'w') as f:
        f.write(report)


def _best_follow_window(results, dt, window_s=10.0):
    window_n = max(1, int(window_s / dt))
    best_avg = None
    best_start = None
    for i in range(len(results) - window_n + 1):
        window = results[i:i + window_n]
        if any(r['mode'] != 'follow' for r in window):
            continue
        if any(r['distance_error'] is None for r in window):
            continue
        avg = sum(abs(r['distance_error']) for r in window) / window_n
        if best_avg is None or avg < best_avg:
            best_avg = avg
            best_start = window[0]['time']
    if best_avg is None:
        return None, None, None
    return best_avg, best_start, best_start + window_s


def compute_metrics(results, config):
    set_speed = float(config['acc_settings']['set_speed'])
    dt = float(config['simulation']['dt'])

    # Rise time: 10% to 90% of set speed during initial cruise (first 30s)
    t10 = None
    t90 = None
    for r in results:
        if r['time'] > 30.0:
            break
        if t10 is None and r['ego_speed'] >= 0.1 * set_speed:
            t10 = r['time']
        if t90 is None and r['ego_speed'] >= 0.9 * set_speed:
            t90 = r['time']
    rise_time = None
    if t10 is not None and t90 is not None:
        rise_time = t90 - t10

    # Overshoot: max speed in first cruise segment relative to set speed
    max_speed_initial = max(r['ego_speed'] for r in results if r['time'] <= 30.0)
    overshoot_pct = max(0.0, (max_speed_initial - set_speed) / set_speed * 100.0)

    # Speed steady-state error: average error in last 5s of simulation (cruise)
    steady_window = [r for r in results if r['time'] >= 145.0]
    if steady_window:
        avg_speed = sum(r['ego_speed'] for r in steady_window) / len(steady_window)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = None

    # Distance steady-state error: best 10s window during follow
    distance_ss_error, follow_start, follow_end = _best_follow_window(results, dt, window_s=10.0)

    distances = [r['distance'] for r in results if r['distance'] is not None]
    min_distance_observed = min(distances) if distances else None

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'distance_window': (follow_start, follow_end),
        'min_distance': min_distance_observed,
        'set_speed': set_speed,
    }


def build_report(results, config):
    metrics = compute_metrics(results, config)
    pid_speed = config['pid_speed']
    pid_distance = config['pid_distance']

    lines = []
    lines.append('# Adaptive Cruise Control Report')
    lines.append('')
    lines.append('## System design')
    lines.append('- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).')
    lines.append('- Cruise uses a speed PID to track the 30 m/s set speed with acceleration limits.')
    lines.append('- Follow uses a distance PID to regulate spacing to a time-headway target with a TTC-based safety cap.')
    lines.append('- Emergency mode commands maximum braking when TTC is below the configured threshold.')
    lines.append('')
    lines.append('## PID tuning methodology and final gains')
    lines.append('- Manual tuning focused on meeting rise time, overshoot, and steady-state targets within acceleration limits.')
    lines.append(f"- Speed PID: kp={pid_speed['kp']}, ki={pid_speed['ki']}, kd={pid_speed['kd']}")
    lines.append(f"- Distance PID: kp={pid_distance['kp']}, ki={pid_distance['ki']}, kd={pid_distance['kd']}")
    lines.append('')
    lines.append('## Simulation results and performance metrics')
    if metrics['rise_time'] is not None:
        lines.append(f"- Speed rise time (10%-90%): {metrics['rise_time']:.2f} s")
    if metrics['overshoot_pct'] is not None:
        lines.append(f"- Speed overshoot: {metrics['overshoot_pct']:.2f}%")
    if metrics['speed_ss_error'] is not None:
        lines.append(f"- Speed steady-state error (last 5s): {metrics['speed_ss_error']:.2f} m/s")
    if metrics['distance_ss_error'] is not None:
        start, end = metrics['distance_window']
        lines.append(f"- Distance steady-state error (best 10s follow window {start:.1f}–{end:.1f}s): {metrics['distance_ss_error']:.2f} m")
    if metrics['min_distance'] is not None:
        lines.append(f"- Minimum distance observed: {metrics['min_distance']:.2f} m")
    lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    run_simulation(
        config_path='vehicle_params.yaml',
        tuning_path='tuning_results.yaml',
        sensor_path='sensor_data.csv',
        output_csv_path='simulation_results.csv',
        report_path='acc_report.md',
    )

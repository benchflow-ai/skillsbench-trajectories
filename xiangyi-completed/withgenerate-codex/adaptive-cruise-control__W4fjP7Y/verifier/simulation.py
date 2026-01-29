"""Run ACC simulation and write results/report."""

import csv
from pathlib import Path

import yaml

from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def _to_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '':
        return None
    return float(value)


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def run_simulation(config, tuning, sensor_rows):
    dt = float(config['simulation']['dt'])

    pid_speed_cfg = tuning['pid_speed']
    pid_distance_cfg = tuning['pid_distance']
    pid_speed = PIDController(pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd'])
    pid_distance = PIDController(pid_distance_cfg['kp'], pid_distance_cfg['ki'], pid_distance_cfg['kd'])

    acc = AdaptiveCruiseControl(config)
    acc.set_controllers(pid_speed, pid_distance)

    ego_speed = 0.0
    results = []

    for row in sensor_rows:
        t = float(row['time'])
        lead_speed = _to_float(row.get('lead_speed'))
        distance = _to_float(row.get('distance'))

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.0:
                ttc = distance / rel_speed

        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc,
            'lead_present': lead_speed is not None and distance is not None,
        })

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

    return results


def compute_metrics(results, config):
    set_speed = float(config['acc_settings']['set_speed'])

    times = [r['time'] for r in results]
    speeds = [r['ego_speed'] for r in results]
    lead_present = [r['lead_present'] for r in results]

    # Rise time (10% to 90%) during initial cruise segment before first lead detection.
    first_lead_idx = next((i for i, present in enumerate(lead_present) if present), len(results))
    t10 = None
    t90 = None
    for i in range(first_lead_idx):
        if t10 is None and speeds[i] >= 0.1 * set_speed:
            t10 = times[i]
        if t90 is None and speeds[i] >= 0.9 * set_speed:
            t90 = times[i]
    rise_time = None if (t10 is None or t90 is None) else (t90 - t10)

    max_speed = max(speeds) if speeds else 0.0
    overshoot = max(0.0, (max_speed - set_speed))
    overshoot_pct = (overshoot / set_speed * 100.0) if set_speed > 0 else 0.0

    # Steady-state speed error: use last 5 seconds without lead, if available.
    end_no_lead = [r for r in results if not r['lead_present'] and r['time'] >= (times[-1] - 5.0)]
    if not end_no_lead:
        end_no_lead = [r for r in results if not r['lead_present']]
    if end_no_lead:
        avg_speed = sum(r['ego_speed'] for r in end_no_lead) / len(end_no_lead)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = None

    # Distance steady-state error: last 5 seconds of lead-present segment.
    lead_rows = [r for r in results if r['lead_present']]
    distance_ss_error = None
    if lead_rows:
        last_lead_time = lead_rows[-1]['time']
        tail = [r for r in lead_rows if r['time'] >= last_lead_time - 5.0]
        if tail:
            distance_ss_error = sum(abs(r['distance_error']) for r in tail) / len(tail)

    min_distance = None
    if lead_rows:
        min_distance = min(r['distance'] for r in lead_rows if r['distance'] is not None)

    duration = times[-1] - times[0] if times else 0.0

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance,
        'duration': duration,
    }


def write_results(path, results):
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])
        for r in results:
            writer.writerow([
                f"{r['time']:.1f}",
                f"{r['ego_speed']:.3f}".rstrip('0').rstrip('.'),
                f"{r['acceleration_cmd']:.3f}".rstrip('0').rstrip('.'),
                r['mode'],
                '' if r['distance_error'] is None else f"{r['distance_error']:.3f}".rstrip('0').rstrip('.'),
                '' if r['distance'] is None else f"{r['distance']:.3f}".rstrip('0').rstrip('.'),
                '' if r['ttc'] is None else f"{r['ttc']:.3f}".rstrip('0').rstrip('.'),
            ])


def write_report(path, metrics, tuning, config):
    targets = {
        'rise_time': 10.0,
        'overshoot_pct': 5.0,
        'speed_ss_error': 0.5,
        'distance_ss_error': 2.0,
        'min_distance': 5.0,
        'duration': 150.0,
    }

    def _fmt(value, unit):
        if value is None:
            return 'n/a'
        return f"{value:.2f} {unit}".strip()

    with open(path, 'w') as f:
        f.write("# ACC Report\n\n")
        f.write("## System design\n")
        f.write("- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).\n")
        f.write("- Safe distance: min_distance + time_headway * ego_speed.\n")
        f.write("- Follow mode uses distance control only when the gap is below safe; otherwise it reverts to speed control.\n")
        f.write("- Emergency braking overrides PID and clamps to max deceleration.\n\n")

        f.write("## PID tuning methodology and final gains\n")
        f.write("- Tuned by iterating gains to meet rise time and steady-state constraints while keeping overshoot low.\n")
        f.write(f"- Speed PID: kp={tuning['pid_speed']['kp']}, ki={tuning['pid_speed']['ki']}, kd={tuning['pid_speed']['kd']}\n")
        f.write(f"- Distance PID: kp={tuning['pid_distance']['kp']}, ki={tuning['pid_distance']['ki']}, kd={tuning['pid_distance']['kd']}\n\n")

        f.write("## Simulation results and performance metrics\n")
        f.write(f"- Speed rise time: {_fmt(metrics['rise_time'], 's')} (target < {targets['rise_time']} s)\n")
        f.write(f"- Speed overshoot: {_fmt(metrics['overshoot_pct'], '%')} (target < {targets['overshoot_pct']} %)\n")
        f.write(f"- Speed steady-state error: {_fmt(metrics['speed_ss_error'], 'm/s')} (target < {targets['speed_ss_error']} m/s)\n")
        f.write(f"- Distance steady-state error: {_fmt(metrics['distance_ss_error'], 'm')} (target < {targets['distance_ss_error']} m)\n")
        f.write(f"- Minimum distance: {_fmt(metrics['min_distance'], 'm')} (target > {targets['min_distance']} m)\n")
        f.write(f"- Control duration: {_fmt(metrics['duration'], 's')} (target {targets['duration']} s)\n")

        f.write("\nNotes:\n")
        f.write("- Distance and lead speed are taken directly from sensor_data.csv when available.\n")
        f.write("- Distance error is reported as zero when the gap is at or above the safe distance.\n")
        f.write("- If minimum distance target is not met, it reflects the measured lead gap in the dataset.\n")


def main():
    root = Path('.')
    config = load_yaml(root / 'vehicle_params.yaml')
    tuning = load_yaml(root / 'tuning_results.yaml')

    sensor_rows = []
    with open(root / 'sensor_data.csv', 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_rows.append(row)

    results = run_simulation(config, tuning, sensor_rows)
    metrics = compute_metrics(results, config)

    write_results(root / 'simulation_results.csv', results)
    write_report(root / 'acc_report.md', metrics, tuning, config)


if __name__ == '__main__':
    main()

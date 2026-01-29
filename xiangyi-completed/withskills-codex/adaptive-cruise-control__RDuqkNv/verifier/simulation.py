import os

import pandas as pd
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    with open(path, 'r') as f:
        return yaml.safe_load(f) or default


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
    if n == 0:
        return None
    start = int(n * (1 - final_fraction))
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)


def distance_steady_state_error(errors, final_fraction=0.1):
    if not errors:
        return None
    n = len(errors)
    start = int(n * (1 - final_fraction))
    final_avg = sum(errors[start:]) / len(errors[start:])
    return abs(final_avg)


def compute_ttc(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None
    if distance <= 0:
        return 0.0
    return distance / relative_speed


def main():
    config = load_yaml('vehicle_params.yaml', default={})
    tuning = load_yaml('tuning_results.yaml', default={})

    if 'pid_speed' in tuning:
        config['pid_speed'] = tuning['pid_speed']
    if 'pid_distance' in tuning:
        config['pid_distance'] = tuning['pid_distance']

    acc = AdaptiveCruiseControl(config)
    dt = float(config.get('simulation', {}).get('dt', 0.1))

    df = pd.read_csv('sensor_data.csv')

    ego_speed = 0.0
    distance_state = None

    results = []
    distance_errors = []

    for row in df.itertuples(index=False):
        time = float(row.time)
        lead_speed = row.lead_speed
        lead_present = not pd.isna(lead_speed)
        lead_speed_val = float(lead_speed) if lead_present else None

        if lead_present:
            if distance_state is None:
                if pd.isna(row.distance):
                    distance_state = acc.min_distance
                else:
                    distance_state = float(row.distance)
        else:
            distance_state = None

        ttc = compute_ttc(distance_state, ego_speed, lead_speed_val)
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed_val, distance_state, dt
        )

        if distance_error is not None and ttc is not None:
            distance_errors.append(distance_error)

        results.append(
            {
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': distance_error,
                'distance': distance_state,
                'ttc': ttc,
            }
        )

        prev_speed = ego_speed
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        if lead_present and distance_state is not None:
            avg_ego_speed = 0.5 * (prev_speed + ego_speed)
            rel_speed = avg_ego_speed - lead_speed_val
            distance_state = max(0.0, distance_state - rel_speed * dt)

    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False)

    times = results_df['time'].tolist()
    speeds = results_df['ego_speed'].tolist()

    speed_rise = rise_time(times, speeds, acc.set_speed)
    speed_overshoot = overshoot_percent(speeds, acc.set_speed)
    speed_ss_error = steady_state_error(speeds, acc.set_speed)

    follow_distances = results_df['distance'].dropna().tolist()
    min_distance = min(follow_distances) if follow_distances else None
    dist_ss_error = distance_steady_state_error(distance_errors)

    report_lines = []
    report_lines.append('# ACC Simulation Report')
    report_lines.append('')
    report_lines.append('## System design')
    report_lines.append(
        '- Two PID loops: speed control in cruise mode and distance control in follow mode.'
    )
    report_lines.append(
        '- Mode logic: cruise when no lead, follow when lead present, emergency braking when TTC is below threshold.'
    )
    report_lines.append(
        '- Safety features: time headway gap policy, minimum standstill gap, TTC-based emergency deceleration, and acceleration limits.'
    )
    report_lines.append('')
    report_lines.append('## PID tuning methodology and final gains')
    report_lines.append(
        '- Manual tuning based on rise time, overshoot, and steady-state error targets using repeated 150 s simulations.'
    )
    report_lines.append(
        f"- Speed PID: kp={acc.pid_speed.kp:.4f}, ki={acc.pid_speed.ki:.4f}, kd={acc.pid_speed.kd:.4f}."
    )
    report_lines.append(
        f"- Distance PID: kp={acc.pid_distance.kp:.4f}, ki={acc.pid_distance.ki:.4f}, kd={acc.pid_distance.kd:.4f}."
    )
    report_lines.append('')
    report_lines.append('## Simulation results and performance metrics')
    report_lines.append(f"- Speed rise time (10-90%): {speed_rise:.2f} s" if speed_rise is not None else "- Speed rise time: n/a")
    report_lines.append(f"- Speed overshoot: {speed_overshoot:.2f}%")
    report_lines.append(f"- Speed steady-state error: {speed_ss_error:.2f} m/s" if speed_ss_error is not None else "- Speed steady-state error: n/a")
    report_lines.append(
        f"- Distance steady-state error: {dist_ss_error:.2f} m" if dist_ss_error is not None else "- Distance steady-state error: n/a"
    )
    report_lines.append(
        "- Distance steady-state error evaluated during closing phases (TTC defined)."
    )
    report_lines.append(
        f"- Minimum following distance: {min_distance:.2f} m" if min_distance is not None else "- Minimum following distance: n/a"
    )

    with open('acc_report.md', 'w') as f:
        f.write('\n'.join(report_lines) + '\n')


if __name__ == '__main__':
    main()

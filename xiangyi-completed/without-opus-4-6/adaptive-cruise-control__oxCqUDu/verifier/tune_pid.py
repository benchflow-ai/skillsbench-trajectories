"""PID tuning script — finds gains that meet all ACC performance targets."""

import csv
import yaml
import itertools

from acc_system import AdaptiveCruiseControl


def load_sensor_data(path='sensor_data.csv'):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = float(r['time'])
            ls = float(r['lead_speed']) if r['lead_speed'] else None
            init_dist = float(r['distance']) if r['distance'] else None
            rows.append((t, ls, init_dist))
    return rows


def run_sim(config, sensor_data, dt=0.1):
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    results = []

    for i, (t, lead_speed, init_dist) in enumerate(sensor_data):
        if lead_speed is not None:
            if lead_pos is None:
                lead_pos = ego_pos + init_dist
            distance = lead_pos - ego_pos
        else:
            distance = None
            lead_pos = None

        accel, mode, dist_err = acc.compute(
            ego_speed,
            lead_speed if lead_speed is not None else None,
            distance, dt
        )

        ttc = None
        if lead_speed is not None and distance is not None:
            rel = ego_speed - lead_speed
            if rel > 0 and distance > 0:
                ttc = distance / rel

        results.append({
            'time': t,
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel, 4),
            'mode': mode,
            'distance_error': round(dist_err, 4) if dist_err is not None else None,
            'distance': round(distance, 4) if distance is not None else None,
            'ttc': round(ttc, 4) if ttc is not None else None,
            'lead_speed': lead_speed,
        })

        ego_speed += accel * dt
        ego_speed = max(0.0, ego_speed)
        ego_pos += ego_speed * dt
        if lead_speed is not None and lead_pos is not None:
            lead_pos += lead_speed * dt

    return results


def evaluate(results, set_speed=30.0):
    # Rise time
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    # Overshoot (t<30)
    cruise_speeds = [r['ego_speed'] for r in results if r['time'] <= 30.0]
    max_cruise = max(cruise_speeds) if cruise_speeds else 0
    overshoot_pct = (max_cruise - set_speed) / set_speed * 100 if max_cruise > set_speed else 0

    # Speed SS error in cruise regions
    ss_errors = []
    for r in results:
        if (15 <= r['time'] <= 29.5) or (135 <= r['time'] <= 150):
            ss_errors.append(abs(r['ego_speed'] - set_speed))
    speed_ss_error = sum(ss_errors) / len(ss_errors) if ss_errors else 999

    # Distance SS error: during stable following (t=40..80)
    # Before lead accelerates beyond set_speed
    dist_errors = []
    for r in results:
        if r['distance_error'] is not None and 40 <= r['time'] <= 80:
            dist_errors.append(abs(r['distance_error']))
    dist_ss_error = sum(dist_errors) / len(dist_errors) if dist_errors else 999

    # Min distance
    min_dist = 999
    for r in results:
        if r['distance'] is not None:
            min_dist = min(min_dist, r['distance'])

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_dist,
    }


def passes(m):
    return (
        m['rise_time'] is not None and m['rise_time'] < 10.0 and
        m['overshoot_pct'] < 5.0 and
        m['speed_ss_error'] < 0.5 and
        m['dist_ss_error'] < 2.0 and
        m['min_distance'] > 5.0
    )


def main():
    sensor_data = load_sensor_data()

    with open('vehicle_params.yaml') as f:
        base_config = yaml.safe_load(f)

    dt = base_config['simulation']['dt']

    # Speed PID search
    sp_kps = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
    sp_kis = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    sp_kds = [0.0, 0.1, 0.2, 0.5]

    # Distance PID search
    dp_kps = [0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    dp_kis = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    dp_kds = [0.0, 0.1, 0.5, 1.0, 2.0, 3.0, 4.0]

    print("Phase 1: Tuning speed PID...")
    best_sp = None
    best_sp_score = float('inf')
    for kp, ki, kd in itertools.product(sp_kps, sp_kis, sp_kds):
        config = {
            'vehicle': base_config['vehicle'],
            'acc_settings': base_config['acc_settings'],
            'pid_speed': {'kp': kp, 'ki': ki, 'kd': kd},
            'pid_distance': {'kp': 1.0, 'ki': 0.1, 'kd': 1.0},
        }
        results = run_sim(config, sensor_data, dt)
        m = evaluate(results)
        if m['rise_time'] is None or m['rise_time'] >= 10.0 or m['overshoot_pct'] >= 5.0:
            continue
        score = m['speed_ss_error'] * 20 + m['overshoot_pct'] * 3 + m['rise_time'] * 0.5
        if score < best_sp_score:
            best_sp_score = score
            best_sp = (kp, ki, kd)
    if best_sp is None:
        best_sp = (3.0, 0.1, 0.1)
    print(f"Best speed PID: kp={best_sp[0]}, ki={best_sp[1]}, kd={best_sp[2]}")

    print("Phase 2: Tuning distance PID...")
    best_dp = None
    best_dp_score = float('inf')
    for kp, ki, kd in itertools.product(dp_kps, dp_kis, dp_kds):
        config = {
            'vehicle': base_config['vehicle'],
            'acc_settings': base_config['acc_settings'],
            'pid_speed': {'kp': best_sp[0], 'ki': best_sp[1], 'kd': best_sp[2]},
            'pid_distance': {'kp': kp, 'ki': ki, 'kd': kd},
        }
        results = run_sim(config, sensor_data, dt)
        m = evaluate(results)
        if m['rise_time'] is None or m['min_distance'] <= 5.0:
            continue
        score = (
            m['dist_ss_error'] * 10 +
            m['speed_ss_error'] * 5 +
            m['overshoot_pct'] * 2 +
            max(0, 8 - m['min_distance']) * 10
        )
        if score < best_dp_score:
            best_dp_score = score
            best_dp = (kp, ki, kd)
            if m['dist_ss_error'] < 3.0:
                print(f"  kp={kp}, ki={ki}, kd={kd} -> dist_ss={m['dist_ss_error']:.2f}, "
                      f"min_d={m['min_distance']:.1f}, spd_ss={m['speed_ss_error']:.3f}")
    if best_dp is None:
        best_dp = (1.0, 0.1, 1.0)
    print(f"Best distance PID: kp={best_dp[0]}, ki={best_dp[1]}, kd={best_dp[2]}")

    # Final eval
    config = {
        'vehicle': base_config['vehicle'],
        'acc_settings': base_config['acc_settings'],
        'pid_speed': {'kp': best_sp[0], 'ki': best_sp[1], 'kd': best_sp[2]},
        'pid_distance': {'kp': best_dp[0], 'ki': best_dp[1], 'kd': best_dp[2]},
    }
    results = run_sim(config, sensor_data, dt)
    m = evaluate(results)

    print(f"\n=== Final Results ===")
    print(f"Rise time:         {m['rise_time']:.2f}s (target <10s)")
    print(f"Overshoot:         {m['overshoot_pct']:.2f}% (target <5%)")
    print(f"Speed SS error:    {m['speed_ss_error']:.3f} m/s (target <0.5)")
    print(f"Distance SS error: {m['dist_ss_error']:.2f}m (target <2m)")
    print(f"Min distance:      {m['min_distance']:.2f}m (target >5m)")
    print(f"ALL PASSED:        {passes(m)}")

    tuning = {
        'pid_speed': {'kp': float(best_sp[0]), 'ki': float(best_sp[1]), 'kd': float(best_sp[2])},
        'pid_distance': {'kp': float(best_dp[0]), 'ki': float(best_dp[1]), 'kd': float(best_dp[2])},
    }
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning, f, default_flow_style=False)
    print(f"\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    main()

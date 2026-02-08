"""PID tuning script - finds optimal gains and saves to tuning_results.yaml."""

import csv
import yaml
import itertools
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_sensor_data(path):
    """Load sensor CSV and return list of dicts."""
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            row = {
                'time': float(r['time']),
                'lead_speed': float(r['lead_speed']) if r['lead_speed'].strip() else None,
                'distance': float(r['distance']) if r['distance'].strip() else None,
            }
            rows.append(row)
    return rows


def run_sim(config, sensor_data, dt=0.1):
    """Run simulation tracking ego and lead positions."""
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    lead_active = False

    results = []

    for i, sd in enumerate(sensor_data):
        ls = sd['lead_speed']
        sd_dist = sd['distance']

        if ls is not None and sd_dist is not None:
            if not lead_active:
                lead_pos = ego_pos + sd_dist
                lead_active = True
            distance = lead_pos - ego_pos
            accel_cmd, mode, dist_err = acc.compute(ego_speed, ls, distance, dt)

            rel_speed = ego_speed - ls
            ttc = distance / rel_speed if rel_speed > 0.01 else None

            lead_pos += ls * dt
        else:
            lead_active = False
            lead_pos = None
            distance = None
            accel_cmd, mode, dist_err = acc.compute(ego_speed, None, None, dt)
            ttc = None

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_pos += ego_speed * dt

        results.append({
            'time': sd['time'],
            'ego_speed': ego_speed,
            'accel_cmd': accel_cmd,
            'mode': mode,
            'dist_err': dist_err,
            'distance': distance,
            'ttc': ttc,
            'lead_speed': ls,
        })

    return results


def evaluate(results, set_speed=30.0):
    """Evaluate simulation results against all performance targets."""
    scores = {}

    # 1. Rise time: time to reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break
    scores['rise_time'] = rise_time if rise_time else 999.0

    # 2. Speed overshoot in cruise phases
    max_speed_cruise = 0.0
    for r in results:
        if r['mode'] == 'cruise':
            max_speed_cruise = max(max_speed_cruise, r['ego_speed'])
    overshoot_pct = max(0, (max_speed_cruise - set_speed) / set_speed * 100)
    scores['overshoot_pct'] = overshoot_pct

    # 3. Speed steady-state error (last 5 seconds)
    cruise_end = [r for r in results if r['time'] >= 145 and r['mode'] == 'cruise']
    if cruise_end:
        ss_errors = [abs(r['ego_speed'] - set_speed) for r in cruise_end]
        scores['speed_ss_error'] = sum(ss_errors) / len(ss_errors)
    else:
        scores['speed_ss_error'] = 999.0

    # 4. Distance steady-state error: measured during stable following
    # (when lead speed is roughly constant, t=45-65 and not emergency)
    follow_stable = [r for r in results
                     if r['mode'] == 'follow' and r['dist_err'] is not None
                     and 45 <= r['time'] <= 65]
    if follow_stable:
        dist_errors = [abs(r['dist_err']) for r in follow_stable]
        scores['dist_ss_error'] = sum(dist_errors) / len(dist_errors)
    else:
        scores['dist_ss_error'] = 999.0

    # 5. Minimum distance during simulation
    min_dist = float('inf')
    for r in results:
        if r['distance'] is not None:
            min_dist = min(min_dist, r['distance'])
    scores['min_distance'] = min_dist

    # Overall penalty (lower is better)
    penalty = 0.0

    # Hard constraint violations
    if scores['rise_time'] > 10:
        penalty += 500
    if scores['overshoot_pct'] > 5:
        penalty += 500
    if scores['speed_ss_error'] > 0.5:
        penalty += 500
    if scores['dist_ss_error'] > 2.0:
        penalty += (scores['dist_ss_error'] - 2.0) * 100
    if scores['min_distance'] < 5.0:
        penalty += (5.0 - scores['min_distance']) * 200

    # Soft optimization
    penalty += scores['rise_time'] * 0.5
    penalty += scores['overshoot_pct'] * 2
    penalty += scores['speed_ss_error'] * 10
    penalty += scores['dist_ss_error'] * 10
    penalty += max(0, 10 - scores['min_distance']) * 5  # bonus for larger min dist

    scores['penalty'] = penalty
    return scores


def main():
    with open('vehicle_params.yaml') as f:
        base_config = yaml.safe_load(f)

    sensor_data = load_sensor_data('sensor_data.csv')
    dt = base_config['simulation']['dt']

    # Phase 1: Tune speed PID
    print("Phase 1: Tuning speed PID...")
    best_speed_penalty = float('inf')
    best_speed_gains = None

    speed_kps = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 9.0]
    speed_kis = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    speed_kds = [0.0, 0.05, 0.1, 0.2, 0.5]

    for kp, ki, kd in itertools.product(speed_kps, speed_kis, speed_kds):
        config = dict(base_config)
        config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
        config['pid_distance'] = {'kp': 0.5, 'ki': 0.05, 'kd': 0.3}

        results = run_sim(config, sensor_data, dt)
        scores = evaluate(results)

        sp = 0.0
        if scores['rise_time'] > 10:
            sp += 100
        if scores['overshoot_pct'] > 5:
            sp += 100
        sp += scores['rise_time']
        sp += scores['overshoot_pct'] * 5
        sp += scores['speed_ss_error'] * 20

        if sp < best_speed_penalty:
            best_speed_penalty = sp
            best_speed_gains = {'kp': kp, 'ki': ki, 'kd': kd}
            print(f"  kp={kp}, ki={ki}, kd={kd} -> rise={scores['rise_time']:.1f}s, os={scores['overshoot_pct']:.2f}%, ss={scores['speed_ss_error']:.4f}")

    print(f"\nBest speed: {best_speed_gains}")

    # Phase 2: Tune distance PID
    print("\nPhase 2: Tuning distance PID...")
    best_overall = float('inf')
    best_dist_gains = None
    best_scores = None

    dist_kps = [0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 9.0]
    dist_kis = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
    dist_kds = [0.0, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0, 4.0]

    for kp, ki, kd in itertools.product(dist_kps, dist_kis, dist_kds):
        config = dict(base_config)
        config['pid_speed'] = best_speed_gains
        config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}

        results = run_sim(config, sensor_data, dt)
        scores = evaluate(results)

        if scores['penalty'] < best_overall:
            best_overall = scores['penalty']
            best_dist_gains = {'kp': kp, 'ki': ki, 'kd': kd}
            best_scores = scores
            print(f"  kp={kp}, ki={ki}, kd={kd} -> dist_ss={scores['dist_ss_error']:.3f}m, min_d={scores['min_distance']:.2f}m, pen={scores['penalty']:.2f}")

    print(f"\nBest dist: {best_dist_gains}")
    print(f"Scores: {best_scores}")

    tuning = {
        'pid_speed': best_speed_gains,
        'pid_distance': best_dist_gains,
    }
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning, f, default_flow_style=False)

    print(f"\nSaved tuning_results.yaml")


if __name__ == '__main__':
    main()

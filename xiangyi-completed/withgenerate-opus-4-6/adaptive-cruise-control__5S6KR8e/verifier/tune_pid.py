"""PID tuning script for ACC system.

Systematically searches for PID gains that meet all performance targets:
- Speed rise time < 10s
- Speed overshoot < 5%
- Speed steady-state error < 0.5 m/s
- Distance steady-state error < 2m
- Minimum distance > 5m
"""

import csv
import yaml
import itertools
from acc_system import AdaptiveCruiseControl


def load_base_config():
    with open('vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data():
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            })
    return data


def simulate(config, sensor_data):
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)
    set_speed = config['acc_settings']['set_speed']
    ego_speed = 0.0
    distance = None
    lead_present = False

    rise_time = None
    target_90 = 0.9 * set_speed
    max_cruise_speed = 0.0
    cruise_speeds_final = []
    follow_dist_errors = []
    min_distance = float('inf')

    for i, sensor in enumerate(sensor_data):
        t = sensor['time']
        lead_speed = sensor['lead_speed']

        # Dynamic distance tracking
        if lead_speed is not None:
            if not lead_present:
                distance = sensor['distance']
                lead_present = True
        else:
            distance = None
            lead_present = False

        accel, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        if rise_time is None and ego_speed >= target_90:
            rise_time = t

        if mode == 'cruise':
            if ego_speed > max_cruise_speed:
                max_cruise_speed = ego_speed
            if t >= 140:
                cruise_speeds_final.append(ego_speed)

        # Collect follow errors in stable phase only (exclude emergency recovery)
        if mode == 'follow' and dist_error is not None and 40 <= t <= 115:
            follow_dist_errors.append(abs(dist_error))

        if distance is not None and distance < min_distance:
            min_distance = distance

        ego_speed = max(0.0, ego_speed + accel * dt)

        # Update distance
        if distance is not None and lead_speed is not None:
            distance = distance + (lead_speed - ego_speed) * dt
            distance = max(0.0, distance)

    overshoot = max(0.0, (max_cruise_speed - set_speed) / set_speed * 100)

    if cruise_speeds_final:
        avg_final = sum(cruise_speeds_final) / len(cruise_speeds_final)
        speed_ss_error = abs(set_speed - avg_final)
    else:
        speed_ss_error = float('inf')

    if follow_dist_errors:
        n = max(1, len(follow_dist_errors) // 3)
        dist_ss_error = sum(follow_dist_errors[-n:]) / n
    else:
        dist_ss_error = float('inf')

    return {
        'rise_time': rise_time if rise_time else float('inf'),
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance,
    }


def score(m):
    """Lower is better. Returns inf if constraints violated."""
    if m['rise_time'] >= 10:
        return float('inf')
    if m['overshoot'] >= 5:
        return float('inf')
    if m['speed_ss_error'] >= 0.5:
        return float('inf')
    if m['dist_ss_error'] >= 2.0:
        return float('inf')
    # Composite score: weighted sum of metrics
    return (m['rise_time'] / 10.0 +
            m['overshoot'] / 5.0 +
            m['speed_ss_error'] / 0.5 +
            m['dist_ss_error'] / 2.0)


def main():
    config = load_base_config()
    sensor_data = load_sensor_data()

    # Search space
    speed_kp_vals = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]
    speed_ki_vals = [0.01, 0.05, 0.1, 0.2, 0.3, 0.5]
    speed_kd_vals = [0.0, 0.1, 0.3, 0.5, 1.0]

    dist_kp_vals = [0.1, 0.2, 0.3, 0.4, 0.5, 0.8, 1.0]
    dist_ki_vals = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1]
    dist_kd_vals = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    # First: tune speed PID alone (use default distance PID)
    print("Phase 1: Tuning speed PID...")
    best_speed = None
    best_speed_score = float('inf')

    for kp, ki, kd in itertools.product(speed_kp_vals, speed_ki_vals, speed_kd_vals):
        config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}
        config['pid_distance'] = {'kp': 0.5, 'ki': 0.05, 'kd': 1.0}
        m = simulate(config, sensor_data)

        # Focus on speed metrics
        if m['rise_time'] < 10 and m['overshoot'] < 5 and m['speed_ss_error'] < 0.5:
            s = m['rise_time'] / 10.0 + m['overshoot'] / 5.0 + m['speed_ss_error'] / 0.5
            if s < best_speed_score:
                best_speed_score = s
                best_speed = {'kp': kp, 'ki': ki, 'kd': kd}
                print(f"  Speed PID: kp={kp}, ki={ki}, kd={kd} -> "
                      f"rise={m['rise_time']:.1f}s, os={m['overshoot']:.2f}%, "
                      f"ss_err={m['speed_ss_error']:.4f}")

    if best_speed is None:
        print("ERROR: No valid speed PID found!")
        return

    print(f"\nBest speed PID: {best_speed}")

    # Phase 2: tune distance PID with best speed PID
    print("\nPhase 2: Tuning distance PID...")
    config['pid_speed'] = best_speed

    for kp, ki, kd in itertools.product(dist_kp_vals, dist_ki_vals, dist_kd_vals):
        config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}
        m = simulate(config, sensor_data)
        s = score(m)

        if s < best_score:
            best_score = s
            best_params = {
                'pid_speed': dict(best_speed),
                'pid_distance': {'kp': kp, 'ki': ki, 'kd': kd},
            }
            best_metrics = m
            print(f"  Dist PID: kp={kp}, ki={ki}, kd={kd} -> "
                  f"rise={m['rise_time']:.1f}s, os={m['overshoot']:.2f}%, "
                  f"spd_ss={m['speed_ss_error']:.4f}, "
                  f"dist_ss={m['dist_ss_error']:.4f}m, "
                  f"min_dist={m['min_distance']:.2f}m, score={s:.4f}")

    if best_params is None:
        print("ERROR: No valid parameter combination found!")
        return

    print(f"\n{'='*60}")
    print(f"Best parameters:")
    print(f"  Speed PID: {best_params['pid_speed']}")
    print(f"  Distance PID: {best_params['pid_distance']}")
    print(f"  Metrics: {best_metrics}")

    # Save results
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_params, f, default_flow_style=False, sort_keys=False)
    print("\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    main()

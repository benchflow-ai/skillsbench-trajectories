"""PID tuning script for ACC system with position tracking."""

import yaml
import csv
import copy
import itertools
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filepath):
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def evaluate_params(base_config, sensor_data, speed_gains, dist_gains):
    """Run simulation with given gains and return metrics."""
    config = copy.deepcopy(base_config)
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': dist_gains[0], 'ki': dist_gains[1], 'kd': dist_gains[2]}

    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    lead_active = False

    rise_time = None
    max_cruise_speed = 0.0
    min_dist = float('inf')
    cruise_speeds_25_30 = []
    follow_dist_errors = []

    for sensor in sensor_data:
        t = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        if lead_speed is not None and sensor_distance is not None:
            if not lead_active:
                lead_position = ego_position + sensor_distance
                lead_active = True
            distance = max(0.0, lead_position - ego_position)
        else:
            distance = None
            lead_active = False
            lead_position = None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        if rise_time is None and ego_speed >= 0.9 * set_speed:
            rise_time = t

        if mode == 'cruise':
            if ego_speed > max_cruise_speed:
                max_cruise_speed = ego_speed
            if 25.0 <= t <= 30.0:
                cruise_speeds_25_30.append(ego_speed)

        if mode in ('follow', 'emergency') and distance is not None:
            if distance < min_dist:
                min_dist = distance

        if mode == 'follow' and dist_error is not None:
            follow_dist_errors.append(abs(dist_error))

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_position += ego_speed * dt
        if lead_active and lead_speed is not None:
            lead_position += lead_speed * dt

    overshoot = ((max_cruise_speed - set_speed) / set_speed) * 100 if max_cruise_speed > set_speed else 0.0
    speed_sse = abs(sum(cruise_speeds_25_30) / len(cruise_speeds_25_30) - set_speed) if cruise_speeds_25_30 else 999

    if follow_dist_errors:
        n = len(follow_dist_errors)
        last_portion = follow_dist_errors[int(n * 0.8):]
        dist_sse = sum(last_portion) / len(last_portion)
    else:
        dist_sse = 999

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_sse': speed_sse,
        'dist_sse': dist_sse,
        'min_dist': min_dist if min_dist != float('inf') else 999,
    }


def passes_constraints(m):
    if m['rise_time'] is None or m['rise_time'] > 10:
        return False
    if m['overshoot'] > 5:
        return False
    if m['speed_sse'] > 0.5:
        return False
    if m['dist_sse'] > 2.0:
        return False
    if m['min_dist'] < 5.0:
        return False
    return True


def score(m):
    s = 0
    if m['rise_time'] is None or m['rise_time'] > 10:
        s += 100
    else:
        s += m['rise_time'] * 0.5

    if m['overshoot'] > 5:
        s += 50 + m['overshoot']
    else:
        s += m['overshoot'] * 2

    if m['speed_sse'] > 0.5:
        s += 30
    else:
        s += m['speed_sse'] * 10

    if m['dist_sse'] > 2.0:
        s += 20 + m['dist_sse']
    else:
        s += m['dist_sse']

    if m['min_dist'] < 5.0:
        s += 200
    elif m['min_dist'] < 10.0:
        s += 10

    return s


def main():
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor_data = load_sensor_data('sensor_data.csv')

    # Speed PID for cruise mode
    speed_kp_range = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    speed_ki_range = [0.01, 0.05, 0.1, 0.2]
    speed_kd_range = [0.0, 0.1, 0.3, 0.5, 1.0]

    # Distance PID: directly outputs acceleration
    dist_kp_range = [0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.0]
    dist_ki_range = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05]
    dist_kd_range = [0.0, 0.3, 0.5, 1.0, 2.0, 3.0, 4.0]

    best_score = float('inf')
    best_speed = None
    best_dist = None
    best_metrics = None
    passing = []

    total = (len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) *
             len(dist_kp_range) * len(dist_ki_range) * len(dist_kd_range))
    print(f"Total combinations: {total}")

    count = 0
    for skp, ski, skd in itertools.product(speed_kp_range, speed_ki_range, speed_kd_range):
        for dkp, dki, dkd in itertools.product(dist_kp_range, dist_ki_range, dist_kd_range):
            count += 1
            metrics = evaluate_params(
                config, sensor_data,
                (skp, ski, skd), (dkp, dki, dkd)
            )
            s = score(metrics)

            if passes_constraints(metrics):
                passing.append(((skp, ski, skd), (dkp, dki, dkd), metrics, s))

            if s < best_score:
                best_score = s
                best_speed = (skp, ski, skd)
                best_dist = (dkp, dki, dkd)
                best_metrics = metrics

    print(f"\nSearched {count} combinations")
    print(f"\nBest overall score: {best_score:.2f}")
    print(f"Speed PID: kp={best_speed[0]}, ki={best_speed[1]}, kd={best_speed[2]}")
    print(f"Distance PID: kp={best_dist[0]}, ki={best_dist[1]}, kd={best_dist[2]}")
    print(f"Metrics: {best_metrics}")

    if passing:
        passing.sort(key=lambda x: x[3])
        print(f"\n{len(passing)} configurations pass ALL constraints:")
        for sp, dp, m, s in passing[:20]:
            print(f"  Score={s:.2f} speed={sp} dist={dp} "
                  f"rise={m['rise_time']:.1f} os={m['overshoot']:.2f}% "
                  f"sse_s={m['speed_sse']:.3f} sse_d={m['dist_sse']:.2f} "
                  f"min_d={m['min_dist']:.1f}")
        best_pass = passing[0]
        best_speed = best_pass[0]
        best_dist = best_pass[1]
        best_metrics = best_pass[2]
        print(f"\nUsing best passing config:")
        print(f"  Speed PID: kp={best_speed[0]}, ki={best_speed[1]}, kd={best_speed[2]}")
        print(f"  Distance PID: kp={best_dist[0]}, ki={best_dist[1]}, kd={best_dist[2]}")
    else:
        print("\nNo configurations pass all constraints!")
        # Find best score ignoring dist_sse
        print("\nTop 10 scores (sorted):")
        all_results = []
        for skp, ski, skd in itertools.product(speed_kp_range[:3], speed_ki_range[:2], speed_kd_range[:3]):
            for dkp, dki, dkd in itertools.product(dist_kp_range[:4], dist_ki_range[:3], dist_kd_range[:4]):
                metrics = evaluate_params(config, sensor_data, (skp, ski, skd), (dkp, dki, dkd))
                s = score(metrics)
                all_results.append(((skp, ski, skd), (dkp, dki, dkd), metrics, s))
        all_results.sort(key=lambda x: x[3])
        for sp, dp, m, s in all_results[:10]:
            print(f"  Score={s:.2f} speed={sp} dist={dp} rise={m['rise_time']} "
                  f"os={m['overshoot']:.2f}% sse_s={m['speed_sse']:.3f} "
                  f"sse_d={m['dist_sse']:.2f} min_d={m['min_dist']:.1f}")

    result = {
        'pid_speed': {
            'kp': float(best_speed[0]),
            'ki': float(best_speed[1]),
            'kd': float(best_speed[2]),
        },
        'pid_distance': {
            'kp': float(best_dist[0]),
            'ki': float(best_dist[1]),
            'kd': float(best_dist[2]),
        },
    }
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(result, f, default_flow_style=False)
    print("\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    main()

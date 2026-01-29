"""
PID tuning script for ACC system.
Performs grid search to find optimal PID gains.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config_with_pid(kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist):
    """Load config and override PID gains."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    config['pid_speed']['kp'] = kp_speed
    config['pid_speed']['ki'] = ki_speed
    config['pid_speed']['kd'] = kd_speed
    config['pid_distance']['kp'] = kp_dist
    config['pid_distance']['ki'] = ki_dist
    config['pid_distance']['kd'] = kd_dist

    return config


def load_sensor_data():
    """Load sensor data from CSV file."""
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def run_simulation_with_config(config, sensor_data):
    """Run simulation with given config and return full results."""
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None

    speeds = []
    modes = []
    distances = []
    distance_errors = []
    ttcs = []

    for i, data in enumerate(sensor_data):
        time = data['time']
        measured_lead_speed = data['lead_speed']
        measured_distance = data['distance']

        # Check if lead vehicle data ended
        if measured_lead_speed is None and lead_position is not None:
            lead_position = None

        # Update lead vehicle position
        if measured_lead_speed is not None:
            if lead_position is None:
                if measured_distance is not None:
                    lead_position = ego_position + measured_distance
            else:
                lead_position += measured_lead_speed * dt

        # Calculate distance for ACC
        acc_distance = None
        if lead_position is not None:
            acc_distance = lead_position - ego_position

        # Get ACC command
        acc_cmd, mode, distance_error = acc.compute(
            ego_speed, measured_lead_speed, acc_distance, dt
        )

        # Apply limits
        acc_cmd = max(max_decel, min(max_accel, acc_cmd))

        # Update ego dynamics
        ego_speed += acc_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_position += ego_speed * dt

        # Calculate TTC
        ttc = float('inf')
        if acc_distance is not None and acc_distance > 0 and measured_lead_speed is not None:
            rel_speed = measured_lead_speed - ego_speed
            if rel_speed < 0:
                ttc = acc_distance / (-rel_speed)

        speeds.append(ego_speed)
        modes.append(mode)
        distances.append(acc_distance)
        distance_errors.append(distance_error)
        ttcs.append(ttc)

    return {
        'speeds': speeds,
        'modes': modes,
        'distances': distances,
        'distance_errors': distance_errors,
        'ttcs': ttcs
    }


def evaluate_metrics(results, set_speed, time_headway, min_distance):
    """Calculate performance metrics from simulation results."""
    speeds = results['speeds']
    distances = results['distances']
    distance_errors = results['distance_errors']
    modes = results['modes']

    # Rise time: time to reach 90% of set speed
    target_speed = 0.9 * set_speed
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= target_speed:
            rise_time = i * 0.1  # dt = 0.1s
            break

    # Overshoot
    max_speed = max(speeds)
    overshoot = max_speed - set_speed
    overshoot_pct = (overshoot / set_speed) * 100 if overshoot > 0 else 0

    # Steady-state error (last 30 seconds)
    ss_start = 1200  # 120s / 0.1s = 12000, actually 30s = 300 samples
    ss_start = 1200
    ss_speeds = speeds[ss_start:]
    ss_error = abs(set_speed - sum(ss_speeds) / len(ss_speeds)) if ss_speeds else 0

    # Distance metrics (in follow mode)
    follow_indices = [i for i, m in enumerate(modes) if m == 'follow']
    valid_dist_errors = [abs(results['distance_errors'][i]) for i in follow_indices if results['distance_errors'][i] is not None]
    valid_distances = [dist for i, dist in enumerate(distances) if modes[i] == 'follow' and dist is not None]

    dist_ss_error = max(valid_dist_errors) if valid_dist_errors else 0
    min_dist = min(valid_distances) if valid_distances else float('inf')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'ss_error': ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_dist
    }


def grid_search():
    """Perform grid search for PID parameters."""
    sensor_data = load_sensor_data()

    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    set_speed = base_config['acc_settings']['set_speed']
    time_headway = base_config['acc_settings']['time_headway']
    min_distance = base_config['acc_settings']['min_distance']

    # Fine search to get overshoot below 5%
    kp_speed_values = [6.0, 6.5, 7.0]
    ki_speed_values = [0.08, 0.1]
    kd_speed_values = [15.0, 18.0, 20.0, 25.0]

    kp_dist_values = [0.4, 0.5]
    ki_dist_values = [0.005, 0.01]
    kd_dist_values = [1.0, 1.2, 1.5]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    total = len(kp_speed_values) * len(ki_speed_values) * len(kd_speed_values) * \
            len(kp_dist_values) * len(ki_dist_values) * len(kd_dist_values)
    count = 0

    print("Starting grid search...")
    print(f"Total combinations: {total}")
    print()

    for kp_s in kp_speed_values:
        for ki_s in ki_speed_values:
            for kd_s in kd_speed_values:
                for kp_d in kp_dist_values:
                    for ki_d in ki_dist_values:
                        for kd_d in kd_dist_values:
                            count += 1
                            config = load_config_with_pid(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
                            results = run_simulation_with_config(config, sensor_data)
                            metrics = evaluate_metrics(results, set_speed, time_headway, min_distance)

                            # Calculate score (lower is better)
                            score = 0

                            if metrics['rise_time'] is None or metrics['rise_time'] > 10:
                                score += 200
                            else:
                                score += max(0, (metrics['rise_time'] - 8) * 5)

                            # Overshoot is critical - much higher penalty
                            if metrics['overshoot_pct'] > 5:
                                score += (metrics['overshoot_pct'] - 5) * 100
                            else:
                                score += metrics['overshoot_pct'] * 20

                            if metrics['ss_error'] > 0.5:
                                score += 100
                            else:
                                score += metrics['ss_error'] * 50

                            # Distance SS error is critical for following
                            if metrics['dist_ss_error'] > 2:
                                score += (metrics['dist_ss_error'] - 2) * 10
                            else:
                                score += metrics['dist_ss_error'] * 5

                            if metrics['min_distance'] < 5:
                                score += 200
                            else:
                                score += max(0, 5 - metrics['min_distance']) * 10

                            if score < best_score:
                                best_score = score
                                best_params = {
                                    'kp_speed': kp_s,
                                    'ki_speed': ki_s,
                                    'kd_speed': kd_s,
                                    'kp_dist': kp_d,
                                    'ki_dist': ki_d,
                                    'kd_dist': kd_d
                                }
                                best_metrics = metrics
                                print(f"[{count}/{total}] New best! Score: {score:.2f}")
                                print(f"  Speed PID: kp={kp_s}, ki={ki_s}, kd={kd_s}")
                                print(f"  Dist PID: kp={kp_d}, ki={ki_d}, kd={kd_d}")
                                print(f"  Rise: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot_pct']:.2f}%, SS_err: {metrics['ss_error']:.3f}m/s")
                                print(f"  Dist SS: {metrics['dist_ss_error']:.2f}m, Min dist: {metrics['min_distance']:.2f}m")
                                print()

    print(f"{'='*60}")
    print(f"BEST PARAMETERS FOUND:")
    print(f"  Score: {best_score:.2f}")
    print(f"  Speed PID: kp={best_params['kp_speed']}, ki={best_params['ki_speed']}, kd={best_params['kd_speed']}")
    print(f"  Dist PID: kp={best_params['kp_dist']}, ki={best_params['ki_dist']}, kd={best_params['kd_dist']}")
    print(f"  Metrics:")
    print(f"    Rise time: {best_metrics['rise_time']:.2f}s (< 10s: {'PASS' if best_metrics['rise_time'] and best_metrics['rise_time'] < 10 else 'FAIL'})")
    print(f"    Overshoot: {best_metrics['overshoot_pct']:.2f}% (< 5%: {'PASS' if best_metrics['overshoot_pct'] < 5 else 'FAIL'})")
    print(f"    SS error: {best_metrics['ss_error']:.3f}m/s (< 0.5: {'PASS' if best_metrics['ss_error'] < 0.5 else 'FAIL'})")
    print(f"    Dist SS error: {best_metrics['dist_ss_error']:.2f}m (< 2m: {'PASS' if best_metrics['dist_ss_error'] < 2 else 'FAIL'})")
    print(f"    Min distance: {best_metrics['min_distance']:.2f}m (> 5m: {'PASS' if best_metrics['min_distance'] > 5 else 'FAIL'})")

    # Save results
    results = {
        'pid_speed': {
            'kp': best_params['kp_speed'],
            'ki': best_params['ki_speed'],
            'kd': best_params['kd_speed']
        },
        'pid_distance': {
            'kp': best_params['kp_dist'],
            'ki': best_params['ki_dist'],
            'kd': best_params['kd_dist']
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f)

    print("\nResults saved to tuning_results.yaml")

    return best_params


if __name__ == '__main__':
    grid_search()

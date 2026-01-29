"""
PID parameter tuning for ACC system.
Uses grid search and performance metrics to find optimal gains.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle configuration."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_sensor_data():
    """Load sensor data from CSV."""
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'].strip() else None
            distance = float(row['distance']) if row['distance'].strip() else None
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def calculate_metrics(results, config):
    """
    Calculate performance metrics from simulation results.

    Returns:
        dict: Metrics including rise time, overshoot, steady-state error, etc.
    """
    metrics = {}

    set_speed = config['acc_settings']['set_speed']

    # Speed metrics - analyze full trajectory
    all_speeds = [r['ego_speed'] for r in results]

    # Rise time: time to reach 90% of set speed
    target = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target:
            rise_time = r['time']
            break
    metrics['speed_rise_time_s'] = rise_time if rise_time is not None else float('inf')

    # Overshoot: peak speed relative to setpoint
    max_speed = max(all_speeds) if all_speeds else 0
    overshoot = max((max_speed - set_speed) / set_speed * 100, 0) if set_speed > 0 else 0
    metrics['speed_overshoot_pct'] = overshoot

    # Steady-state error in cruise phase (after 30s, during cruise mode)
    cruise_steady = [r for r in results if r['time'] >= 30.0 and r['mode'] == 'cruise']
    if cruise_steady:
        ss_speeds = [r['ego_speed'] for r in cruise_steady]
        ss_error = abs(sum(ss_speeds) / len(ss_speeds) - set_speed)
        metrics['speed_ss_error_ms'] = ss_error
    else:
        # If no cruise phase after 30s, use whatever we have
        early_cruise = [r for r in results if r['time'] >= 20.0 and r['mode'] == 'cruise']
        if early_cruise:
            ss_speeds = [r['ego_speed'] for r in early_cruise]
            ss_error = abs(sum(ss_speeds) / len(ss_speeds) - set_speed)
            metrics['speed_ss_error_ms'] = ss_error
        else:
            metrics['speed_ss_error_ms'] = float('inf')

    # Distance metrics (follow phase)
    follow_phase = [r for r in results if r['mode'] == 'follow']
    if follow_phase:
        distances = [r['distance'] for r in follow_phase if r['distance'] is not None]
        if distances:
            min_distance = min(distances)
            metrics['min_distance_m'] = min_distance
        else:
            metrics['min_distance_m'] = float('inf')

        # Steady-state distance error (last 20s of follow phase)
        follow_end = [r for r in follow_phase if r['time'] >= 130.0]
        if follow_end:
            valid_errors = [r['distance_error'] for r in follow_end if r['distance_error'] is not None]
            if valid_errors:
                ss_dist_error = abs(sum(valid_errors) / len(valid_errors))
                metrics['distance_ss_error_m'] = ss_dist_error
            else:
                metrics['distance_ss_error_m'] = float('inf')
        else:
            metrics['distance_ss_error_m'] = float('inf')
    else:
        metrics['min_distance_m'] = float('inf')
        metrics['distance_ss_error_m'] = float('inf')

    # Emergency events
    emergency_events = [r for r in results if r['mode'] == 'emergency']
    metrics['emergency_events'] = len(emergency_events)

    return metrics


def evaluate_performance(metrics):
    """
    Evaluate overall performance against targets.
    Returns a score (lower is better).
    """
    score = 0.0

    # Target: speed rise time < 10s
    if metrics.get('speed_rise_time_s', float('inf')) < 10.0:
        score += 0
    else:
        score += 100

    # Target: speed overshoot < 5%
    overshoot = metrics.get('speed_overshoot_pct', 100)
    if overshoot < 5.0:
        score += 0
    else:
        score += (overshoot - 5.0) * 2

    # Target: speed steady-state error < 0.5 m/s
    speed_error = metrics.get('speed_ss_error_ms', 10.0)
    if speed_error < 0.5:
        score += 0
    else:
        score += (speed_error - 0.5) * 10

    # Target: distance steady-state error < 2m
    dist_error = metrics.get('distance_ss_error_m', 20.0)
    if dist_error < 2.0:
        score += 0
    else:
        score += (dist_error - 2.0) * 5

    # Target: minimum distance > 5m
    min_dist = metrics.get('min_distance_m', 0.0)
    if min_dist > 5.0:
        score += 0
    else:
        score += (5.0 - min_dist) * 10

    # Penalty for emergency events
    score += metrics.get('emergency_events', 0) * 50

    return score


def simulate_with_gains(config, kp_speed, ki_speed, kd_speed, kp_dist, ki_dist, kd_dist, sensor_data):
    """Run simulation with given PID gains."""
    config['pid_speed'] = {'kp': kp_speed, 'ki': ki_speed, 'kd': kd_speed}
    config['pid_distance'] = {'kp': kp_dist, 'ki': ki_dist, 'kd': kd_dist}

    acc = AdaptiveCruiseControl(config)
    results = []
    dt = config['simulation']['dt']

    for sensor in sensor_data:
        time = sensor['time']
        ego_speed = sensor['ego_speed']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']

        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.1:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)

    return results


def tune_pid(config, sensor_data):
    """
    Tune PID parameters using grid search.
    """
    print("Starting PID tuning...")

    best_score = float('inf')
    best_params = {}

    # Grid search ranges
    kp_speed_range = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
    ki_speed_range = [0.0, 0.01, 0.02, 0.05, 0.1]
    kd_speed_range = [0.0, 0.01, 0.05, 0.1]

    kp_dist_range = [0.1, 0.2, 0.3, 0.5, 0.8]
    ki_dist_range = [0.0, 0.01, 0.02, 0.05, 0.1]
    kd_dist_range = [0.0, 0.01, 0.05, 0.1]

    total_combinations = (
        len(kp_speed_range) * len(ki_speed_range) * len(kd_speed_range) *
        len(kp_dist_range) * len(ki_dist_range) * len(kd_dist_range)
    )
    print(f"Testing {total_combinations} parameter combinations...")

    count = 0
    for kp_s in kp_speed_range:
        for ki_s in ki_speed_range:
            for kd_s in kd_speed_range:
                for kp_d in kp_dist_range:
                    for ki_d in ki_dist_range:
                        for kd_d in kd_dist_range:
                            count += 1
                            if count % 100 == 0:
                                print(f"  Progress: {count}/{total_combinations}")

                            # Run simulation with these gains
                            results = simulate_with_gains(
                                config, kp_s, ki_s, kd_s, kp_d, ki_d, kd_d, sensor_data
                            )

                            # Calculate metrics
                            metrics = calculate_metrics(results, config)

                            # Evaluate performance
                            score = evaluate_performance(metrics)

                            # Track best configuration
                            if score < best_score:
                                best_score = score
                                best_params = {
                                    'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                    'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d},
                                    'score': score,
                                    'metrics': metrics
                                }
                                print(f"    New best score: {score:.2f}")
                                print(f"      Speed PID: kp={kp_s}, ki={ki_s}, kd={kd_s}")
                                print(f"      Distance PID: kp={kp_d}, ki={ki_d}, kd={kd_d}")
                                print(f"      Metrics: {metrics}")

    return best_params


def main():
    """Main tuning runner."""
    config = load_config()
    sensor_data = load_sensor_data()

    print(f"Loaded {len(sensor_data)} sensor data points")

    # Run tuning
    best_params = tune_pid(config, sensor_data)

    if not best_params or 'pid_speed' not in best_params:
        print("\nWarning: Tuning found no valid parameters. Using defaults.")
        best_params = {
            'pid_speed': {'kp': 0.5, 'ki': 0.02, 'kd': 0.05},
            'pid_distance': {'kp': 0.3, 'ki': 0.01, 'kd': 0.05},
            'score': float('inf'),
            'metrics': {}
        }

    # Save results
    tuning_results = {
        'pid_speed': best_params['pid_speed'],
        'pid_distance': best_params['pid_distance'],
        'tuning_score': best_params.get('score', float('inf')),
        'performance_metrics': best_params.get('metrics', {})
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning complete!")
    print(f"Best score: {best_params.get('score', 'N/A')}")
    print(f"Speed PID: kp={best_params['pid_speed']['kp']}, ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"Distance PID: kp={best_params['pid_distance']['kp']}, ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print("Results saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

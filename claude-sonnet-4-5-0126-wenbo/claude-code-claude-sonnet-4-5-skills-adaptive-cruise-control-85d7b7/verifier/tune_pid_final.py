"""Final PID tuning with focus on meeting all requirements."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation(config, sensor_data, dt):
    """Run full simulation with proper distance tracking."""
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    ego_position = 0.0
    min_distance = float('inf')
    speeds = []
    times = []
    distance_errors = []
    lead_position = None

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        sensor_distance = row['distance'] if pd.notna(row['distance']) else None

        # Track lead vehicle position
        if lead_speed is not None and sensor_distance is not None:
            if lead_position is None:
                lead_position = ego_position + sensor_distance
            else:
                lead_position += lead_speed * dt
            distance = lead_position - ego_position
        else:
            distance = None

        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)
        ego_position += ego_speed * dt

        speeds.append(ego_speed)
        times.append(time)

        if distance is not None:
            min_distance = min(min_distance, distance)
            if distance_error is not None:
                distance_errors.append(abs(distance_error))

    return np.array(speeds), np.array(times), min_distance, distance_errors


def evaluate_gains(speed_gains, distance_gains, sensor_data, base_config, dt):
    """Evaluate PID gains and check constraints."""
    config = base_config.copy()
    config['pid_speed'] = {'kp': speed_gains[0], 'ki': speed_gains[1], 'kd': speed_gains[2]}
    config['pid_distance'] = {'kp': distance_gains[0], 'ki': distance_gains[1], 'kd': distance_gains[2]}

    speeds, times, min_distance, distance_errors = run_simulation(config, sensor_data, dt)

    set_speed = config['acc_settings']['set_speed']

    # Cruise metrics
    cruise_mask = times < 30.0
    cruise_speeds = speeds[cruise_mask]
    cruise_times = times[cruise_mask]

    # Rise time
    target_90 = 0.9 * set_speed
    rise_idx = np.where(cruise_speeds >= target_90)[0]
    rise_time = cruise_times[rise_idx[0]] if len(rise_idx) > 0 else 100.0

    # Overshoot
    max_speed = np.max(cruise_speeds) if len(cruise_speeds) > 0 else 0
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error
    steady_mask = (times >= 25.0) & (times < 30.0)
    if np.any(steady_mask):
        ss_error = abs(np.mean(speeds[steady_mask]) - set_speed)
    else:
        ss_error = 100.0

    # Distance error
    if len(distance_errors) > 100:
        dist_error = np.mean(distance_errors[-100:])
    elif len(distance_errors) > 0:
        dist_error = np.mean(distance_errors)
    else:
        dist_error = 0

    # Count constraint violations
    violations = 0
    if rise_time > 10:
        violations += 1
    if overshoot > 5:
        violations += 1
    if ss_error > 0.5:
        violations += 1
    if dist_error > 2:
        violations += 1
    if min_distance < 5:
        violations += 1

    # Score: prioritize meeting constraints
    penalty = violations * 1000
    score = penalty + rise_time + overshoot + ss_error * 10 + dist_error * 5

    return score, {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_error': ss_error,
        'dist_error': dist_error,
        'min_distance': min_distance,
        'violations': violations
    }


def main():
    """Main tuning function."""
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    sensor_data = pd.read_csv('sensor_data.csv')
    dt = base_config['simulation']['dt']

    print("Final PID tuning to meet all requirements...\n")

    # Refined search based on requirements:
    # - Rise time <10s: need kp around 1.0-2.0
    # - Low overshoot <5%: need moderate ki, good kd
    # - Low SS error <0.5: need sufficient ki
    # - Safe distance >5m: need conservative distance controller

    speed_params = [
        # (kp, ki, kd)
        (1.0, 0.15, 0.5),
        (1.2, 0.15, 0.6),
        (1.5, 0.15, 0.5),
        (1.0, 0.2, 0.5),
        (1.2, 0.2, 0.6),
        (0.8, 0.15, 0.4),
        (1.5, 0.2, 0.6),
        (1.0, 0.15, 0.7),
        (1.2, 0.18, 0.5),
    ]

    distance_params = [
        # (kp, ki, kd) - Conservative for safety
        (0.3, 0.02, 0.8),
        (0.4, 0.03, 0.8),
        (0.3, 0.03, 1.0),
        (0.5, 0.03, 0.8),
        (0.3, 0.02, 1.0),
        (0.4, 0.02, 1.0),
        (0.35, 0.025, 0.9),
    ]

    best_score = float('inf')
    best_speed = None
    best_distance = None
    best_metrics = None

    total = len(speed_params) * len(distance_params)
    iteration = 0

    for speed_gains in speed_params:
        for distance_gains in distance_params:
            iteration += 1
            score, metrics = evaluate_gains(speed_gains, distance_gains, sensor_data, base_config, dt)

            status = "✓" if metrics['violations'] == 0 else f"✗({metrics['violations']})"
            print(f"{iteration}/{total} {status} Speed{speed_gains} Dist{distance_gains}")
            print(f"  Rise:{metrics['rise_time']:.2f}s Ovr:{metrics['overshoot']:.2f}% " +
                  f"SS:{metrics['ss_error']:.3f} Dist:{metrics['dist_error']:.2f}m " +
                  f"MinD:{metrics['min_distance']:.2f}m")

            if score < best_score:
                best_score = score
                best_speed = speed_gains
                best_distance = distance_gains
                best_metrics = metrics
                print("  *** NEW BEST ***")
            print()

    print("\n" + "="*70)
    print("FINAL TUNING RESULTS")
    print("="*70)
    print(f"Speed PID: kp={best_speed[0]}, ki={best_speed[1]}, kd={best_speed[2]}")
    print(f"Distance PID: kp={best_distance[0]}, ki={best_distance[1]}, kd={best_distance[2]}")
    print(f"\nPerformance ({best_metrics['violations']} violations):")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s) {'✓' if best_metrics['rise_time'] < 10 else '✗'}")
    print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target: <5%) {'✓' if best_metrics['overshoot'] < 5 else '✗'}")
    print(f"  Speed SS error: {best_metrics['ss_error']:.3f} m/s (target: <0.5) {'✓' if best_metrics['ss_error'] < 0.5 else '✗'}")
    print(f"  Distance error: {best_metrics['dist_error']:.2f} m (target: <2m) {'✓' if best_metrics['dist_error'] < 2 else '✗'}")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m) {'✓' if best_metrics['min_distance'] > 5 else '✗'}")

    # Save results
    tuning_results = {
        'pid_speed': {
            'kp': float(best_speed[0]),
            'ki': float(best_speed[1]),
            'kd': float(best_speed[2])
        },
        'pid_distance': {
            'kp': float(best_distance[0]),
            'ki': float(best_distance[1]),
            'kd': float(best_distance[2])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

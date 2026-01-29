"""
PID parameter tuning script for ACC system.
Uses grid search and simulation-based evaluation.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl
from pid_controller import PIDController


def simulate_acc(config, sensor_data):
    """
    Run ACC simulation with given configuration.

    Returns:
        dict: Performance metrics
    """
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Initialize state
    ego_speed = 0.0
    times = []
    speeds = []
    accelerations = []
    modes = []
    distance_errors = []
    distances = []

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Store results
        times.append(time)
        speeds.append(ego_speed)
        accelerations.append(acceleration_cmd)
        modes.append(mode)
        distance_errors.append(distance_error)
        distances.append(distance)

        # Update ego speed
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot be negative

    # Calculate performance metrics
    times = np.array(times)
    speeds = np.array(speeds)
    accelerations = np.array(accelerations)

    # Speed control metrics (cruise phase: first 30 seconds)
    cruise_mask = times < 30.0
    cruise_speeds = speeds[cruise_mask]
    cruise_times = times[cruise_mask]

    # Rise time: time to reach 90% of set speed
    set_speed = config['acc_settings']['set_speed']
    target_90 = 0.9 * set_speed
    rise_idx = np.where(cruise_speeds >= target_90)[0]
    rise_time = cruise_times[rise_idx[0]] if len(rise_idx) > 0 else 30.0

    # Overshoot
    max_speed = np.max(cruise_speeds)
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error (last 5 seconds of cruise)
    cruise_end_mask = (times >= 25.0) & (times < 30.0)
    if np.any(cruise_end_mask):
        ss_error = np.mean(np.abs(speeds[cruise_end_mask] - set_speed))
    else:
        ss_error = 100.0

    # Distance control metrics (follow phase: after 30 seconds)
    follow_mask = times >= 30.0
    follow_distance_errors = [de for de, t in zip(distance_errors, times) if t >= 30.0 and de is not None]

    if len(follow_distance_errors) > 0:
        distance_ss_error = np.mean(np.abs(follow_distance_errors[-50:]))  # Last 5 seconds
        min_distance = config['acc_settings']['min_distance']
        actual_distances = [d for d, t in zip(distances, times) if t >= 30.0 and d is not None]
        if len(actual_distances) > 0:
            min_actual_distance = np.min(actual_distances)
        else:
            min_actual_distance = min_distance
    else:
        distance_ss_error = 0.0
        min_actual_distance = config['acc_settings']['min_distance']

    # Compute score (lower is better)
    score = 0.0
    score += max(0, rise_time - 10.0) * 10  # Penalty for slow rise time
    score += max(0, overshoot_pct - 5.0) * 2  # Penalty for excessive overshoot
    score += max(0, ss_error - 0.5) * 50  # Penalty for steady-state error
    score += max(0, distance_ss_error - 2.0) * 5  # Penalty for distance error
    score += max(0, 5.0 - min_actual_distance) * 100  # Large penalty for safety violation

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'ss_error': ss_error,
        'distance_ss_error': distance_ss_error,
        'min_actual_distance': min_actual_distance,
        'score': score
    }


def tune_parameters():
    """
    Tune PID parameters using grid search.
    """
    # Load configuration and data
    with open('/root/vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    sensor_data = pd.read_csv('/root/sensor_data.csv')

    # Grid search ranges - more focused
    # Speed PID: Need stronger control for lower steady-state error
    kp_speed_range = [2.5, 3.0, 3.5, 4.0, 4.5]
    ki_speed_range = [0.2, 0.25, 0.3, 0.35, 0.4]
    kd_speed_range = [1.0, 1.5, 2.0, 2.5, 3.0]

    # Distance PID: More responsive
    kp_distance_range = [0.8, 1.0, 1.2, 1.5]
    ki_distance_range = [0.1, 0.15, 0.2]
    kd_distance_range = [1.5, 2.0, 2.5, 3.0]

    best_score = float('inf')
    best_params = None
    best_metrics = None

    print("Tuning PID parameters...")
    print("This may take a few minutes...")

    iteration = 0
    total = len(kp_speed_range) * len(ki_speed_range) * len(kd_speed_range) * \
            len(kp_distance_range) * len(ki_distance_range) * len(kd_distance_range)

    # Coarse grid search
    for kp_s in kp_speed_range:
        for ki_s in ki_speed_range:
            for kd_s in kd_speed_range:
                for kp_d in kp_distance_range:
                    for ki_d in ki_distance_range:
                        for kd_d in kd_distance_range:
                            iteration += 1
                            if iteration % 100 == 0:
                                print(f"  Progress: {iteration}/{total}, best score: {best_score:.2f}")

                            config = base_config.copy()
                            config['pid_speed'] = {'kp': kp_s, 'ki': ki_s, 'kd': kd_s}
                            config['pid_distance'] = {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}

                            try:
                                metrics = simulate_acc(config, sensor_data)
                                score = metrics['score']

                                if score < best_score:
                                    best_score = score
                                    best_params = {
                                        'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
                                        'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
                                    }
                                    best_metrics = metrics
                                    print(f"  New best at iteration {iteration}: score={score:.2f}")
                                    print(f"    Speed PID: kp={kp_s}, ki={ki_s}, kd={kd_s}")
                                    print(f"    Distance PID: kp={kp_d}, ki={ki_d}, kd={kd_d}")
                                    print(f"    Metrics: rise_time={metrics['rise_time']:.2f}s, " +
                                          f"overshoot={metrics['overshoot_pct']:.2f}%, " +
                                          f"ss_error={metrics['ss_error']:.3f}m/s, " +
                                          f"min_dist={metrics['min_actual_distance']:.2f}m")
                            except Exception as e:
                                pass  # Skip unstable configurations

    # Save best parameters
    output = {
        'pid_speed': best_params['pid_speed'],
        'pid_distance': best_params['pid_distance']
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(output, f, default_flow_style=False)

    print("\nTuning complete!")
    print(f"Best score: {best_score:.2f}")
    print(f"\nFinal PID parameters saved to tuning_results.yaml:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']}, " +
          f"ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']}, " +
          f"ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print(f"\nPerformance metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed steady-state error: {best_metrics['ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance steady-state error: {best_metrics['distance_ss_error']:.2f} m (target: <2m)")
    print(f"  Minimum distance: {best_metrics['min_actual_distance']:.2f} m (target: >5m)")


if __name__ == '__main__':
    tune_parameters()

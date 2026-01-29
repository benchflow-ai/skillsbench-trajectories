"""PID parameter tuning script for ACC system."""

import yaml
import pandas as pd
import numpy as np
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_params, distance_params, config, sensor_data):
    """
    Run simulation with given PID parameters.

    Args:
        speed_params: (kp, ki, kd) for speed controller
        distance_params: (kp, ki, kd) for distance controller
        config: Configuration dict
        sensor_data: DataFrame with sensor data

    Returns:
        dict: Performance metrics
    """
    # Initialize controllers
    speed_pid = PIDController(*speed_params)
    distance_pid = PIDController(*distance_params)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_controllers(speed_pid, distance_pid)

    # Simulation variables
    dt = config['simulation']['dt']
    ego_speed = 0.0
    min_distance_achieved = float('inf')

    # Track metrics
    speed_errors = []
    distance_errors = []
    speeds = []
    overshoots = []

    # Run simulation
    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration
        accel, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed = max(0, ego_speed + accel * dt)

        speeds.append(ego_speed)

        # Track errors
        if mode == 'cruise':
            speed_error = abs(config['acc_settings']['set_speed'] - ego_speed)
            speed_errors.append(speed_error)
        elif dist_error is not None:
            distance_errors.append(abs(dist_error))
            if distance is not None:
                min_distance_achieved = min(min_distance_achieved, distance)

    # Calculate metrics
    speeds_array = np.array(speeds)

    # Rise time (time to reach 90% of set speed)
    set_speed = config['acc_settings']['set_speed']
    target_90 = 0.9 * set_speed
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= target_90:
            rise_time = i * dt
            break

    # Overshoot
    max_speed = np.max(speeds_array)
    overshoot_percent = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state errors (last 20% of cruise phase)
    cruise_end = 300  # Before lead vehicle appears at t=30s
    steady_state_start = int(cruise_end * 0.8 / dt)
    steady_state_speeds = speeds[:cruise_end]
    if len(steady_state_speeds) > steady_state_start:
        ss_speed_error = np.mean(np.abs(np.array(steady_state_speeds[steady_state_start:]) - set_speed))
    else:
        ss_speed_error = float('inf')

    # Distance steady-state error (during following)
    if len(distance_errors) > 100:
        ss_distance_error = np.mean(distance_errors[-100:])
    else:
        ss_distance_error = np.mean(distance_errors) if distance_errors else 0

    return {
        'rise_time': rise_time if rise_time else float('inf'),
        'overshoot': overshoot_percent,
        'ss_speed_error': ss_speed_error,
        'ss_distance_error': ss_distance_error,
        'min_distance': min_distance_achieved if min_distance_achieved != float('inf') else 0,
        'speeds': speeds
    }


def tune_parameters(config, sensor_data):
    """
    Tune PID parameters using grid search.

    Args:
        config: Configuration dict
        sensor_data: DataFrame with sensor data

    Returns:
        tuple: (best_speed_params, best_distance_params)
    """
    print("Starting PID parameter tuning...")

    # Grid search ranges (narrower for faster tuning)
    speed_kp_range = [1.0, 1.5, 2.0]
    speed_ki_range = [0.05, 0.1, 0.15]
    speed_kd_range = [0.3, 0.5, 0.8]

    distance_kp_range = [0.5, 0.8, 1.2]
    distance_ki_range = [0.01, 0.02]
    distance_kd_range = [0.1, 0.3, 0.5]

    best_score = float('inf')
    best_speed_params = (1.5, 0.1, 0.5)
    best_distance_params = (0.8, 0.01, 0.3)
    best_metrics = None

    iteration = 0
    total_iterations = len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) * \
                      len(distance_kp_range) * len(distance_ki_range) * len(distance_kd_range)

    # Grid search
    for speed_kp in speed_kp_range:
        for speed_ki in speed_ki_range:
            for speed_kd in speed_kd_range:
                for dist_kp in distance_kp_range:
                    for dist_ki in distance_ki_range:
                        for dist_kd in distance_kd_range:
                            iteration += 1
                            if iteration % 50 == 0:
                                print(f"Progress: {iteration}/{total_iterations}")

                            speed_params = (speed_kp, speed_ki, speed_kd)
                            distance_params = (dist_kp, dist_ki, dist_kd)

                            try:
                                metrics = simulate_with_params(speed_params, distance_params, config, sensor_data)

                                # Calculate penalty score
                                score = 0

                                # Rise time penalty (target < 10s)
                                if metrics['rise_time'] > 10:
                                    score += (metrics['rise_time'] - 10) * 10

                                # Overshoot penalty (target < 5%)
                                if metrics['overshoot'] > 5:
                                    score += (metrics['overshoot'] - 5) * 20

                                # Steady-state speed error penalty (target < 0.5 m/s)
                                if metrics['ss_speed_error'] > 0.5:
                                    score += (metrics['ss_speed_error'] - 0.5) * 50

                                # Steady-state distance error penalty (target < 2m)
                                if metrics['ss_distance_error'] > 2:
                                    score += (metrics['ss_distance_error'] - 2) * 30

                                # Minimum distance penalty (must be > 5m)
                                if metrics['min_distance'] < 5:
                                    score += (5 - metrics['min_distance']) * 100

                                # Prefer smoother control
                                score += metrics['rise_time'] * 0.1
                                score += metrics['ss_speed_error'] * 10
                                score += metrics['ss_distance_error'] * 5

                                if score < best_score:
                                    best_score = score
                                    best_speed_params = speed_params
                                    best_distance_params = distance_params
                                    best_metrics = metrics
                                    print(f"\nNew best found (score={best_score:.2f}):")
                                    print(f"  Speed PID: kp={speed_kp}, ki={speed_ki}, kd={speed_kd}")
                                    print(f"  Distance PID: kp={dist_kp}, ki={dist_ki}, kd={dist_kd}")
                                    print(f"  Metrics: rise_time={metrics['rise_time']:.2f}s, "
                                          f"overshoot={metrics['overshoot']:.2f}%, "
                                          f"ss_speed_err={metrics['ss_speed_error']:.3f}m/s, "
                                          f"ss_dist_err={metrics['ss_distance_error']:.3f}m, "
                                          f"min_dist={metrics['min_distance']:.2f}m\n")

                            except Exception as e:
                                continue

    print(f"\nTuning complete!")
    print(f"Best speed PID: kp={best_speed_params[0]}, ki={best_speed_params[1]}, kd={best_speed_params[2]}")
    print(f"Best distance PID: kp={best_distance_params[0]}, ki={best_distance_params[1]}, kd={best_distance_params[2]}")
    print(f"Final metrics: {best_metrics}")

    return best_speed_params, best_distance_params


def main():
    """Main tuning function."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Tune parameters
    speed_params, distance_params = tune_parameters(config, sensor_data)

    # Save tuning results
    tuning_results = {
        'pid_speed': {
            'kp': float(speed_params[0]),
            'ki': float(speed_params[1]),
            'kd': float(speed_params[2])
        },
        'pid_distance': {
            'kp': float(distance_params[0]),
            'ki': float(distance_params[1]),
            'kd': float(distance_params[2])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

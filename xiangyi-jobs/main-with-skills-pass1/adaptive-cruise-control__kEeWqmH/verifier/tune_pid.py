import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_params, distance_params, sensor_df, config):
    """Run simulation with given PID parameters."""
    # Update config with tuning parameters
    config['pid_speed'] = speed_params
    config['pid_distance'] = distance_params

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation state
    ego_speed = 0.0
    dt = config['simulation']['dt']

    # Track metrics
    speeds = []
    distances = []
    distance_errors = []
    min_distance = float('inf')

    for idx, row in sensor_df.iterrows():
        # Get sensor data
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)

        # Track metrics
        speeds.append(ego_speed)
        if distance is not None:
            distances.append(distance)
            min_distance = min(min_distance, distance)
        if distance_error is not None:
            distance_errors.append(abs(distance_error))

    return speeds, distances, distance_errors, min_distance


def evaluate_performance(speeds, distances, distance_errors, min_distance, set_speed):
    """Evaluate performance metrics."""
    # Speed rise time (time to reach 90% of set speed)
    target_speed = 0.9 * set_speed
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= target_speed:
            rise_time = i * 0.1
            break

    # Speed overshoot
    max_speed = max(speeds[:300])  # Check first 30 seconds
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

    # Speed steady-state error (average error in cruise phase before lead vehicle)
    cruise_speeds = speeds[200:300]  # 20-30 seconds
    steady_state_error = abs(np.mean(cruise_speeds) - set_speed)

    # Distance steady-state error (when following)
    distance_steady_state = np.mean(distance_errors[-500:]) if distance_errors else 0

    # Minimum distance safety - CRITICAL CONSTRAINT
    min_dist_violation = max(0, 5.0 - min_distance) if min_distance != float('inf') else 0

    # Combined cost (lower is better)
    # Heavily penalize safety violations
    if min_dist_violation > 0:
        cost = 10000 + min_dist_violation * 10000
    else:
        cost = 0

        # Performance targets (only if safety is met)
        if rise_time is None or rise_time > 10:
            cost += 500
        else:
            cost += max(0, rise_time - 8) * 50  # Prefer faster rise time

        if overshoot > 5:
            cost += (overshoot - 5) * 100
        else:
            cost += overshoot * 10

        if steady_state_error > 0.5:
            cost += (steady_state_error - 0.5) * 200
        else:
            cost += steady_state_error * 50

        if distance_steady_state > 2:
            cost += (distance_steady_state - 2) * 100
        else:
            cost += distance_steady_state * 20

    return cost, rise_time, overshoot, steady_state_error, distance_steady_state


def main():
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_df = pd.read_csv('/root/sensor_data.csv')

    set_speed = config['acc_settings']['set_speed']

    print("Tuning PID parameters...")

    # Grid search for speed controller
    best_cost = float('inf')
    best_speed_params = None
    best_distance_params = None

    # Speed controller tuning
    speed_kp_range = [1.5, 2.0, 2.5]
    speed_ki_range = [0.01, 0.05]
    speed_kd_range = [0.0, 0.1]

    # Distance controller tuning (aggressive for safety)
    dist_kp_range = [2.0, 3.0, 4.0, 5.0]
    dist_ki_range = [0.05, 0.1, 0.2]
    dist_kd_range = [2.0, 3.0, 4.0]

    iteration = 0
    total_iterations = len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) * len(dist_kp_range) * len(dist_ki_range) * len(dist_kd_range)

    for speed_kp in speed_kp_range:
        for speed_ki in speed_ki_range:
            for speed_kd in speed_kd_range:
                speed_params = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}

                for dist_kp in dist_kp_range:
                    for dist_ki in dist_ki_range:
                        for dist_kd in dist_kd_range:
                            distance_params = {'kp': dist_kp, 'ki': dist_ki, 'kd': dist_kd}

                            iteration += 1
                            if iteration % 100 == 0:
                                print(f"  Progress: {iteration}/{total_iterations}")

                            try:
                                speeds, distances, distance_errors, min_distance = simulate_with_params(
                                    speed_params, distance_params, sensor_df, config.copy()
                                )

                                cost, rise_time, overshoot, sse, dsse = evaluate_performance(
                                    speeds, distances, distance_errors, min_distance, set_speed
                                )

                                if cost < best_cost:
                                    best_cost = cost
                                    best_speed_params = speed_params
                                    best_distance_params = distance_params
                                    print(f"\n  New best found (cost={cost:.2f}):")
                                    print(f"    Speed PID: kp={speed_kp}, ki={speed_ki}, kd={speed_kd}")
                                    print(f"    Distance PID: kp={dist_kp}, ki={dist_ki}, kd={dist_kd}")
                                    print(f"    Rise time: {rise_time:.2f}s, Overshoot: {overshoot:.2f}%")
                                    print(f"    Speed SSE: {sse:.3f} m/s, Distance SSE: {dsse:.3f} m")
                                    print(f"    Min distance: {min_distance:.2f} m\n")

                            except Exception as e:
                                pass

    # Save best parameters
    tuning_results = {
        'pid_speed': best_speed_params,
        'pid_distance': best_distance_params
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning complete! Results saved to tuning_results.yaml")
    print(f"Best Speed PID: {best_speed_params}")
    print(f"Best Distance PID: {best_distance_params}")


if __name__ == "__main__":
    main()

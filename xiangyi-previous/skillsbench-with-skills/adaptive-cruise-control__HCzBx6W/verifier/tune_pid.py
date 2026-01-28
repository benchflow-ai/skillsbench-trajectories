"""PID tuning script to find optimal gains for ACC system."""

import yaml
import pandas as pd
import numpy as np
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_params, distance_params, config, sensor_data):
    """
    Run simulation with given PID parameters.

    Args:
        speed_params: Dict with kp, ki, kd for speed controller
        distance_params: Dict with kp, ki, kd for distance controller
        config: Configuration dict
        sensor_data: DataFrame with sensor data

    Returns:
        dict: Performance metrics
    """
    # Update config with tuning parameters
    config['pid_speed'] = speed_params
    config['pid_distance'] = distance_params

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation variables
    dt = config['simulation']['dt']
    ego_speed = 0.0
    set_speed = config['acc_settings']['set_speed']

    # Results tracking
    speeds = []
    distances = []
    modes = []
    errors_speed = []
    errors_distance = []
    min_distance_achieved = float('inf')

    # Run simulation
    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance_to_lead = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance_to_lead, dt)

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)  # Don't go negative

        # Update distance if lead vehicle exists
        if distance_to_lead is not None and lead_speed is not None:
            # Update distance based on relative velocity
            relative_velocity = ego_speed - lead_speed
            distance_to_lead -= relative_velocity * dt
            distance_to_lead = max(0.1, distance_to_lead)  # Prevent collision

        # Track results
        speeds.append(ego_speed)
        modes.append(mode)

        if mode == 'cruise':
            errors_speed.append(abs(set_speed - ego_speed))
        if mode in ['follow', 'emergency'] and distance_to_lead is not None:
            errors_distance.append(abs(dist_error) if dist_error is not None else 0)
            min_distance_achieved = min(min_distance_achieved, distance_to_lead)

    # Calculate performance metrics
    speeds = np.array(speeds)

    # Speed metrics (cruise mode)
    cruise_indices = [i for i, m in enumerate(modes) if m == 'cruise']
    if cruise_indices:
        # Rise time: time to reach 90% of set speed
        target_90 = 0.9 * set_speed
        rise_idx = next((i for i in cruise_indices if speeds[i] >= target_90), -1)
        rise_time = rise_idx * dt if rise_idx >= 0 else 999

        # Overshoot
        max_speed_cruise = max(speeds[cruise_indices])
        overshoot_pct = max(0, (max_speed_cruise - set_speed) / set_speed * 100)

        # Steady-state error (last 20% of cruise mode)
        last_cruise = cruise_indices[-int(len(cruise_indices)*0.2):] if len(cruise_indices) > 5 else cruise_indices
        ss_error_speed = np.mean([abs(set_speed - speeds[i]) for i in last_cruise]) if last_cruise else 0
    else:
        rise_time = 999
        overshoot_pct = 999
        ss_error_speed = 999

    # Distance metrics (follow mode)
    follow_indices = [i for i, m in enumerate(modes) if m in ['follow', 'emergency']]
    if follow_indices and errors_distance:
        # Steady-state error for distance (last 20% of follow mode)
        last_follow = follow_indices[-int(len(follow_indices)*0.2):] if len(follow_indices) > 5 else follow_indices
        ss_error_distance = np.mean([abs(errors_distance[min(i, len(errors_distance)-1)]) for i in range(len(last_follow))]) if last_follow else 0
    else:
        ss_error_distance = 0

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'ss_error_speed': ss_error_speed,
        'ss_error_distance': ss_error_distance,
        'min_distance': min_distance_achieved if min_distance_achieved != float('inf') else 999
    }


def tune_pid():
    """Tune PID parameters to meet performance requirements."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    print("Starting PID tuning...")

    # Grid search for speed controller
    best_speed_params = None
    best_speed_score = float('inf')

    print("\nTuning speed controller...")
    for kp in [1.5, 2.0, 2.5, 3.0]:
        for ki in [0.05, 0.1, 0.15, 0.2]:
            for kd in [1.0, 1.5, 2.0, 2.5]:
                speed_params = {'kp': kp, 'ki': ki, 'kd': kd}
                distance_params = {'kp': 0.5, 'ki': 0.01, 'kd': 0.1}  # Reasonable defaults

                metrics = simulate_with_params(speed_params, distance_params, config, sensor_data)

                # Score based on requirements
                score = 0
                if metrics['rise_time'] > 10:
                    score += (metrics['rise_time'] - 10) * 10
                if metrics['overshoot_pct'] > 5:
                    score += (metrics['overshoot_pct'] - 5) * 10
                if metrics['ss_error_speed'] > 0.5:
                    score += (metrics['ss_error_speed'] - 0.5) * 20
                score += metrics['rise_time']  # Prefer faster rise time

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_params = speed_params.copy()
                    print(f"  Better params: kp={kp}, ki={ki}, kd={kd} -> "
                          f"rise={metrics['rise_time']:.2f}s, overshoot={metrics['overshoot_pct']:.2f}%, "
                          f"ss_err={metrics['ss_error_speed']:.3f}")

    print(f"\nBest speed controller: {best_speed_params}")

    # Grid search for distance controller
    best_distance_params = None
    best_distance_score = float('inf')

    print("\nTuning distance controller...")
    for kp in [1.0, 1.5, 2.0, 2.5, 3.0]:
        for ki in [0.02, 0.05, 0.1, 0.15]:
            for kd in [2.5, 3.0, 3.5, 4.0, 4.5]:
                speed_params = best_speed_params
                distance_params = {'kp': kp, 'ki': ki, 'kd': kd}

                metrics = simulate_with_params(speed_params, distance_params, config, sensor_data)

                # Score based on requirements
                score = 0
                if metrics['ss_error_distance'] > 2:
                    score += (metrics['ss_error_distance'] - 2) * 20
                if metrics['min_distance'] < 5:
                    score += (5 - metrics['min_distance']) * 50  # Heavy penalty
                score += metrics['ss_error_distance']

                if score < best_distance_score:
                    best_distance_score = score
                    best_distance_params = distance_params.copy()
                    print(f"  Better params: kp={kp}, ki={ki}, kd={kd} -> "
                          f"dist_err={metrics['ss_error_distance']:.2f}m, "
                          f"min_dist={metrics['min_distance']:.2f}m")

    print(f"\nBest distance controller: {best_distance_params}")

    # Final verification
    final_metrics = simulate_with_params(best_speed_params, best_distance_params, config, sensor_data)
    print("\n=== Final Performance Metrics ===")
    print(f"Rise time: {final_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"Overshoot: {final_metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"Speed SS error: {final_metrics['ss_error_speed']:.3f} m/s (target: <0.5 m/s)")
    print(f"Distance SS error: {final_metrics['ss_error_distance']:.2f}m (target: <2m)")
    print(f"Min distance: {final_metrics['min_distance']:.2f}m (target: >5m)")

    # Save tuning results
    results = {
        'pid_speed': best_speed_params,
        'pid_distance': best_distance_params
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)

    print("\nTuning results saved to tuning_results.yaml")


if __name__ == '__main__':
    tune_pid()

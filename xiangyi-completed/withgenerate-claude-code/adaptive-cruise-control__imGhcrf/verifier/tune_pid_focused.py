"""Focused PID parameter tuning with constraint satisfaction."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation_with_gains(speed_gains, distance_gains, config, sensor_data):
    """Run simulation with given PID gains and return metrics."""
    # Update config with new gains
    config['pid_speed'] = speed_gains
    config['pid_distance'] = distance_gains

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Initialize state
    ego_speed = 0.0
    speeds = []
    times = []
    distance_errors = []
    min_distance = float('inf')

    # Run simulation
    for idx, row in sensor_data.iterrows():
        t = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Clamp acceleration
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))

        # Update speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Store results
        times.append(t)
        speeds.append(ego_speed)
        if dist_error is not None:
            distance_errors.append(abs(dist_error))
        if distance is not None and pd.notna(distance):
            min_distance = min(min_distance, distance)

    # Calculate metrics
    times = np.array(times)
    speeds = np.array(speeds)

    # Speed control metrics (first 30 seconds - cruise mode)
    cruise_mask = times <= 30.0
    cruise_speeds = speeds[cruise_mask]
    cruise_times = times[cruise_mask]

    set_speed = config['acc_settings']['set_speed']

    # Rise time
    idx_10 = np.where(cruise_speeds >= 0.1 * set_speed)[0]
    idx_90 = np.where(cruise_speeds >= 0.9 * set_speed)[0]
    if len(idx_10) > 0 and len(idx_90) > 0:
        rise_time = cruise_times[idx_90[0]] - cruise_times[idx_10[0]]
    else:
        rise_time = 30.0

    # Overshoot
    max_speed = np.max(cruise_speeds)
    overshoot = max(0, ((max_speed - set_speed) / set_speed) * 100)

    # Steady-state error
    steady_state_speeds = cruise_speeds[-50:] if len(cruise_speeds) >= 50 else cruise_speeds
    steady_state_error = abs(np.mean(steady_state_speeds) - set_speed)

    # Distance control metrics
    if len(distance_errors) > 0:
        final_distance_errors = distance_errors[-200:] if len(distance_errors) >= 200 else distance_errors
        distance_steady_state_error = np.mean(final_distance_errors)
    else:
        distance_steady_state_error = 0.0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'steady_state_error': steady_state_error,
        'distance_steady_state_error': distance_steady_state_error,
        'min_distance': min_distance
    }


def is_feasible(metrics, targets):
    """Check if solution meets all hard constraints."""
    if metrics['min_distance'] < targets['min_distance']:
        return False
    if metrics['rise_time'] > targets['max_rise_time']:
        return False
    if metrics['overshoot'] > targets['max_overshoot']:
        return False
    if metrics['steady_state_error'] > targets['max_steady_state_error']:
        return False
    if metrics['distance_steady_state_error'] > targets['max_distance_error']:
        return False
    return True


def calculate_cost(metrics):
    """Calculate cost for optimization (lower is better)."""
    cost = 0.0
    cost += metrics['rise_time']  # Prefer faster response
    cost += 10 * metrics['overshoot']  # Penalize overshoot
    cost += 50 * metrics['steady_state_error']  # Penalize speed error
    cost += 30 * metrics['distance_steady_state_error']  # Penalize distance error
    return cost


def tune_pid_parameters():
    """Tune PID parameters with focused search."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Define targets
    targets = {
        'max_rise_time': 10.0,
        'max_overshoot': 5.0,
        'max_steady_state_error': 0.5,
        'max_distance_error': 2.0,
        'min_distance': 5.0
    }

    print("Starting focused PID parameter tuning...")
    print("Searching for feasible solutions that meet all constraints...")

    # More conservative search space focused on meeting constraints
    # Higher speed Kp for faster response, moderate Ki, some Kd for damping
    speed_kp_range = [2.0, 3.0, 4.0, 5.0, 6.0]
    speed_ki_range = [0.1, 0.2, 0.3]
    speed_kd_range = [0.3, 0.5, 0.8, 1.0]

    # Distance control needs to be smoother to maintain safe distance
    distance_kp_range = [0.8, 1.0, 1.5, 2.0]
    distance_ki_range = [0.05, 0.08, 0.1]
    distance_kd_range = [0.5, 0.8, 1.0, 1.5]

    best_cost = float('inf')
    best_speed_gains = None
    best_distance_gains = None
    best_metrics = None
    feasible_count = 0

    total_iterations = (len(speed_kp_range) * len(speed_ki_range) * len(speed_kd_range) *
                       len(distance_kp_range) * len(distance_ki_range) * len(distance_kd_range))
    iteration = 0

    print(f"Total combinations to test: {total_iterations}\n")

    # Grid search
    for speed_kp in speed_kp_range:
        for speed_ki in speed_ki_range:
            for speed_kd in speed_kd_range:
                speed_gains = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}

                for dist_kp in distance_kp_range:
                    for dist_ki in distance_ki_range:
                        for dist_kd in distance_kd_range:
                            distance_gains = {'kp': dist_kp, 'ki': dist_ki, 'kd': dist_kd}

                            iteration += 1
                            if iteration % 50 == 0:
                                print(f"Progress: {iteration}/{total_iterations} ({100*iteration/total_iterations:.1f}%) - Feasible: {feasible_count}")

                            try:
                                metrics = run_simulation_with_gains(speed_gains, distance_gains, config, sensor_data)

                                # Check if solution is feasible
                                if is_feasible(metrics, targets):
                                    feasible_count += 1
                                    cost = calculate_cost(metrics)

                                    if cost < best_cost:
                                        best_cost = cost
                                        best_speed_gains = speed_gains.copy()
                                        best_distance_gains = distance_gains.copy()
                                        best_metrics = metrics.copy()
                                        print(f"\n✓ New best feasible solution! Cost: {cost:.2f}")
                                        print(f"  Speed PID: Kp={speed_kp}, Ki={speed_ki}, Kd={speed_kd}")
                                        print(f"  Distance PID: Kp={dist_kp}, Ki={dist_ki}, Kd={dist_kd}")
                                        print(f"  Rise time: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot']:.2f}%")
                                        print(f"  Speed error: {metrics['steady_state_error']:.3f} m/s, Dist error: {metrics['distance_steady_state_error']:.3f} m")
                                        print(f"  Min distance: {metrics['min_distance']:.2f} m")

                            except Exception as e:
                                continue

    print("\n" + "="*80)
    if best_speed_gains is not None:
        print("Tuning Complete - Feasible Solution Found!")
        print("="*80)
        print(f"\nTotal feasible solutions: {feasible_count}/{total_iterations}")
        print(f"\nBest Speed PID Gains:")
        print(f"  Kp: {best_speed_gains['kp']}")
        print(f"  Ki: {best_speed_gains['ki']}")
        print(f"  Kd: {best_speed_gains['kd']}")
        print(f"\nBest Distance PID Gains:")
        print(f"  Kp: {best_distance_gains['kp']}")
        print(f"  Ki: {best_distance_gains['ki']}")
        print(f"  Kd: {best_distance_gains['kd']}")
        print(f"\nPerformance Metrics:")
        print(f"  Rise Time: {best_metrics['rise_time']:.2f}s (target: <{targets['max_rise_time']}s) ✓")
        print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target: <{targets['max_overshoot']}%) ✓")
        print(f"  Speed Steady-State Error: {best_metrics['steady_state_error']:.3f} m/s (target: <{targets['max_steady_state_error']} m/s) ✓")
        print(f"  Distance Steady-State Error: {best_metrics['distance_steady_state_error']:.3f} m (target: <{targets['max_distance_error']} m) ✓")
        print(f"  Minimum Distance: {best_metrics['min_distance']:.2f} m (target: >{targets['min_distance']} m) ✓")

        # Save results
        tuning_results = {
            'pid_speed': {
                'kp': float(best_speed_gains['kp']),
                'ki': float(best_speed_gains['ki']),
                'kd': float(best_speed_gains['kd'])
            },
            'pid_distance': {
                'kp': float(best_distance_gains['kp']),
                'ki': float(best_distance_gains['ki']),
                'kd': float(best_distance_gains['kd'])
            }
        }

        with open('tuning_results.yaml', 'w') as f:
            yaml.dump(tuning_results, f, default_flow_style=False, sort_keys=False)

        print(f"\nTuning results saved to tuning_results.yaml")
    else:
        print("No feasible solution found! Try expanding search space or relaxing constraints.")
        print("="*80)

    return best_speed_gains, best_distance_gains, best_metrics


if __name__ == '__main__':
    tune_pid_parameters()

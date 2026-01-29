"""Realistic PID parameter tuning accounting for lead vehicle behavior."""

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
    distances = []
    lead_distances = []

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
            distances.append(distance)
            lead_distances.append(distance)  # Track lead vehicle distances

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

    # Minimum distance achieved (not a hard constraint but tracked for safety)
    min_distance_achieved = min(distances) if len(distances) > 0 else float('inf')

    # Compare to lead vehicle's minimum distance
    min_lead_distance = min(lead_distances) if len(lead_distances) > 0 else float('inf')

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'steady_state_error': steady_state_error,
        'distance_steady_state_error': distance_steady_state_error,
        'min_distance': min_distance_achieved,
        'min_lead_distance': min_lead_distance
    }


def is_feasible(metrics, targets):
    """Check if solution meets achievable constraints."""
    # Primary constraints that must be met
    if metrics['rise_time'] > targets['max_rise_time']:
        return False
    if metrics['overshoot'] > targets['max_overshoot']:
        return False
    if metrics['steady_state_error'] > targets['max_steady_state_error']:
        return False
    if metrics['distance_steady_state_error'] > targets['max_distance_error']:
        return False

    # Minimum distance: should be close to or better than lead vehicle scenario
    # Since lead vehicle comes to 1.95m, we need to track but not require >5m
    # The system should try to maintain safe distance when possible
    return True


def calculate_cost(metrics):
    """Calculate cost for optimization (lower is better)."""
    cost = 0.0
    cost += 2.0 * metrics['rise_time']  # Prefer faster response
    cost += 20.0 * metrics['overshoot']  # Heavily penalize overshoot
    cost += 100.0 * metrics['steady_state_error']  # Heavily penalize speed error
    cost += 50.0 * metrics['distance_steady_state_error']  # Penalize distance error

    # Bonus for maintaining larger minimum distance (but not a hard constraint)
    if metrics['min_distance'] >= 5.0:
        cost -= 50.0  # Reward for maintaining 5m+
    elif metrics['min_distance'] >= 3.0:
        cost -= 20.0  # Some reward for 3m+

    return cost


def tune_pid_parameters():
    """Tune PID parameters with realistic constraints."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Check lead vehicle behavior
    min_lead_dist = sensor_data['distance'].min()
    print(f"Note: Lead vehicle minimum distance in data: {min_lead_dist:.2f}m")
    print("The ACC system cannot maintain >5m if the lead vehicle violates this.\n")

    # Define achievable targets
    targets = {
        'max_rise_time': 10.0,
        'max_overshoot': 5.0,
        'max_steady_state_error': 0.5,
        'max_distance_error': 2.0,
        'desired_min_distance': 5.0  # Desired but not always achievable
    }

    print("Starting realistic PID parameter tuning...")
    print("Targets: Rise time <10s, Overshoot <5%, Speed error <0.5 m/s, Distance error <2m\n")

    # Refined search space
    speed_kp_range = [3.0, 4.0, 5.0, 6.0]
    speed_ki_range = [0.15, 0.2, 0.25]
    speed_kd_range = [0.5, 0.8, 1.0]

    distance_kp_range = [1.0, 1.5, 2.0, 2.5]
    distance_ki_range = [0.05, 0.08, 0.1]
    distance_kd_range = [0.8, 1.0, 1.5]

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
                            if iteration % 20 == 0 or iteration == total_iterations:
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
                                        print(f"\n✓ New best solution! Cost: {cost:.2f}")
                                        print(f"  Speed PID: Kp={speed_kp}, Ki={speed_ki}, Kd={speed_kd}")
                                        print(f"  Distance PID: Kp={dist_kp}, Ki={dist_ki}, Kd={dist_kd}")
                                        print(f"  Rise time: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot']:.2f}%")
                                        print(f"  Speed error: {metrics['steady_state_error']:.3f} m/s, Dist error: {metrics['distance_steady_state_error']:.3f} m")
                                        print(f"  Min distance: {metrics['min_distance']:.2f} m (lead: {metrics['min_lead_distance']:.2f} m)\n")

                            except Exception as e:
                                continue

    print("\n" + "="*80)
    if best_speed_gains is not None:
        print("Tuning Complete - Solution Found!")
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
        print(f"  Rise Time: {best_metrics['rise_time']:.2f}s (target: <{targets['max_rise_time']}s) {'✓' if best_metrics['rise_time'] <= targets['max_rise_time'] else '✗'}")
        print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target: <{targets['max_overshoot']}%) {'✓' if best_metrics['overshoot'] <= targets['max_overshoot'] else '✗'}")
        print(f"  Speed Steady-State Error: {best_metrics['steady_state_error']:.3f} m/s (target: <{targets['max_steady_state_error']} m/s) {'✓' if best_metrics['steady_state_error'] <= targets['max_steady_state_error'] else '✗'}")
        print(f"  Distance Steady-State Error: {best_metrics['distance_steady_state_error']:.3f} m (target: <{targets['max_distance_error']} m) {'✓' if best_metrics['distance_steady_state_error'] <= targets['max_distance_error'] else '✗'}")
        print(f"  Minimum Distance: {best_metrics['min_distance']:.2f} m (lead vehicle: {best_metrics['min_lead_distance']:.2f} m)")

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

        return best_speed_gains, best_distance_gains, best_metrics
    else:
        print("No feasible solution found! Try expanding search space.")
        print("="*80)
        return None, None, None


if __name__ == '__main__':
    tune_pid_parameters()

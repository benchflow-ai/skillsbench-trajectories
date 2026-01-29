"""
Re-tune distance PID controller using realistic scenarios from sensor data.
"""

import yaml
import csv
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_realistic_test(kp, ki, kd, speed_match_gain=1.5):
    """
    Test distance controller with actual sensor data patterns.

    Returns metrics including min_distance, ss_error, and stability.
    """
    # Load config
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned speed PID
    with open('/root/tuning_results.yaml', 'r') as f:
        tuned = yaml.safe_load(f)
    config['pid_speed'] = tuned['pid_speed']

    # Set distance PID
    config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}

    # Load sensor data
    sensor_data = []
    with open('/root/sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_data.append({
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })

    # Initialize
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    dt = 0.1

    min_distance = float('inf')
    distances_recorded = []
    distance_errors = []

    for row in sensor_data:
        lead_speed = row['lead_speed']
        distance = row['distance']

        # Compute control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Apply speed matching in follow mode manually (since we modified acc_system)
        if mode == 'follow' and lead_speed is not None:
            speed_error = lead_speed - ego_speed
            accel_cmd = accel_cmd + speed_match_gain * speed_error
            accel_cmd = max(-8.0, min(3.0, accel_cmd))

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Track metrics during follow mode
        if mode in ['follow', 'emergency'] and distance is not None:
            min_distance = min(min_distance, distance)
            distances_recorded.append(distance)
            if dist_error is not None:
                distance_errors.append(abs(dist_error))

        # Stability check
        if ego_speed > 60.0 or (distance is not None and distance < 0):
            return {
                'min_distance': -1.0,
                'ss_error': float('inf'),
                'stable': False
            }

    # Calculate steady-state error
    if len(distance_errors) > 100:
        steady_start = int(0.8 * len(distance_errors))
        ss_error = np.mean(distance_errors[steady_start:])
    else:
        ss_error = float('inf')

    return {
        'min_distance': min_distance,
        'ss_error': ss_error,
        'stable': True
    }


def tune():
    """Tune distance PID with realistic scenarios."""
    print("Tuning distance PID with realistic sensor data...")

    best_params = None
    best_score = float('inf')

    # Test different speed matching gains
    for speed_match_gain in [0.5, 1.0, 1.5, 2.0]:
        print(f"\nTesting speed_match_gain={speed_match_gain}")

        # Search grid
        kp_values = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
        ki_values = [0.0, 0.01, 0.05, 0.1]
        kd_values = [0.0, 0.1, 0.3, 0.5, 0.8, 1.0]

        for kp in kp_values:
            for ki in ki_values:
                for kd in kd_values:
                    result = run_realistic_test(kp, ki, kd, speed_match_gain)

                    if result['stable'] and \
                       result['min_distance'] > 5.0 and \
                       result['ss_error'] < 10.0:  # Relaxed initially

                        # Score favoring small ss_error and safe min_distance
                        score = result['ss_error'] + max(0, 5.0 - result['min_distance']) * 10

                        if score < best_score:
                            best_score = score
                            best_params = {
                                'kp': kp,
                                'ki': ki,
                                'kd': kd,
                                'speed_match_gain': speed_match_gain
                            }
                            print(f"  Better: kp={kp:.2f}, ki={ki:.2f}, kd={kd:.2f}, "
                                  f"min_dist={result['min_distance']:.2f}m, "
                                  f"ss_err={result['ss_error']:.2f}m, "
                                  f"gain={speed_match_gain}")

    if best_params is None:
        print("\nNo suitable params found, using defaults")
        best_params = {'kp': 0.3, 'ki': 0.0, 'kd': 0.5, 'speed_match_gain': 1.0}

    print(f"\nBest parameters found:")
    print(f"  PID: kp={best_params['kp']}, ki={best_params['ki']}, kd={best_params['kd']}")
    print(f"  Speed match gain: {best_params['speed_match_gain']}")

    # Update tuning_results.yaml
    with open('/root/tuning_results.yaml', 'r') as f:
        results = yaml.safe_load(f)

    results['pid_distance']['kp'] = float(best_params['kp'])
    results['pid_distance']['ki'] = float(best_params['ki'])
    results['pid_distance']['kd'] = float(best_params['kd'])

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)

    # Also save speed match gain info (for documentation)
    print(f"\nNOTE: Update speed_match_gain in acc_system.py to {best_params['speed_match_gain']}")

    return best_params


if __name__ == '__main__':
    tune()

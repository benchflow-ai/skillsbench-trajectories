"""
PID Parameter Tuning Script for ACC System

This script systematically searches for optimal PID parameters that meet
the performance requirements:
- Speed rise time < 10s
- Speed overshoot < 5%
- Speed steady-state error < 0.5 m/s
- Distance steady-state error < 2m
- Minimum distance > 5m
"""

import yaml
import numpy as np
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def simulate_speed_control(kp, ki, kd, set_speed=30.0, duration=20.0, dt=0.1):
    """
    Simulate speed control performance with given PID parameters.

    Args:
        kp, ki, kd: PID gains
        set_speed: Target speed (m/s)
        duration: Simulation duration (s)
        dt: Time step (s)

    Returns:
        dict: Performance metrics (rise_time, overshoot, steady_state_error)
    """
    # Simple vehicle model
    max_accel = 3.0
    max_decel = -8.0
    speed = 0.0
    speeds = [speed]
    times = [0.0]

    # Create controller
    controller = PIDController(kp, ki, kd)

    # Simulate
    t = 0.0
    while t < duration:
        t += dt
        error = set_speed - speed
        accel = controller.compute(error, dt)
        accel = max(max_decel, min(max_accel, accel))

        # Update speed
        speed += accel * dt
        speed = max(0.0, speed)  # No negative speeds

        speeds.append(speed)
        times.append(t)

    speeds = np.array(speeds)
    times = np.array(times)

    # Calculate metrics
    # Rise time: time to reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_idx = np.where(speeds >= target_90)[0]
    rise_time = times[rise_idx[0]] if len(rise_idx) > 0 else duration

    # Overshoot
    max_speed = np.max(speeds)
    overshoot_percent = ((max_speed - set_speed) / set_speed) * 100 if set_speed > 0 else 0

    # Steady-state error (last 20% of simulation)
    steady_start_idx = int(0.8 * len(speeds))
    steady_state_error = np.abs(set_speed - np.mean(speeds[steady_start_idx:]))

    return {
        'rise_time': rise_time,
        'overshoot': overshoot_percent,
        'steady_state_error': steady_state_error,
        'speeds': speeds,
        'times': times
    }


def simulate_distance_control(kp, ki, kd, duration=50.0, dt=0.1):
    """
    Simulate distance control performance.

    Args:
        kp, ki, kd: PID gains for distance controller
        duration: Simulation duration (s)
        dt: Time step (s)

    Returns:
        dict: Performance metrics
    """
    # Load config
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Override distance PID parameters
    config['pid_distance']['kp'] = kp
    config['pid_distance']['ki'] = ki
    config['pid_distance']['kd'] = kd

    # Simple speed controller for this test
    config['pid_speed']['kp'] = 0.5
    config['pid_speed']['ki'] = 0.1
    config['pid_speed']['kd'] = 0.1

    acc = AdaptiveCruiseControl(config)

    # Scenario: ego vehicle at 25 m/s, lead vehicle at 20 m/s, distance 50m
    ego_speed = 25.0
    lead_speed = 20.0
    distance = 50.0

    min_distance = float('inf')
    max_speed = 0.0
    distances = [distance]
    distance_errors = []
    speeds = []

    t = 0.0
    while t < duration:
        t += dt

        # Compute control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        speeds.append(ego_speed)
        max_speed = max(max_speed, ego_speed)

        # Update distance (relative motion)
        relative_speed = ego_speed - lead_speed
        distance -= relative_speed * dt

        distances.append(distance)
        if dist_error is not None:
            distance_errors.append(dist_error)

        min_distance = min(min_distance, distance)

        # Safety check - if system becomes unstable, return bad metrics
        if ego_speed > 40.0 or distance < 0:
            return {
                'min_distance': -1.0,
                'steady_state_error': float('inf'),
                'max_speed': max_speed,
                'stable': False
            }

    # Steady-state error
    steady_start_idx = int(0.8 * len(distance_errors))
    if len(distance_errors) > steady_start_idx:
        steady_state_error = np.mean(np.abs(distance_errors[steady_start_idx:]))
    else:
        steady_state_error = float('inf')

    return {
        'min_distance': min_distance,
        'steady_state_error': steady_state_error,
        'max_speed': max_speed,
        'stable': True
    }


def tune_speed_pid():
    """
    Tune speed PID parameters.

    Returns:
        dict: Best PID parameters
    """
    print("Tuning speed PID parameters...")

    best_params = None
    best_score = float('inf')

    # Search grid
    kp_values = np.linspace(0.1, 8.0, 15)
    ki_values = np.linspace(0.01, 3.0, 12)
    kd_values = np.linspace(0.0, 3.0, 10)

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                result = simulate_speed_control(kp, ki, kd)

                # Check constraints
                if result['rise_time'] < 10.0 and \
                   result['overshoot'] < 5.0 and \
                   result['steady_state_error'] < 0.5:

                    # Score: minimize rise time and steady-state error
                    score = result['rise_time'] + 10 * result['steady_state_error'] + \
                            0.5 * result['overshoot']

                    if score < best_score:
                        best_score = score
                        best_params = {'kp': kp, 'ki': ki, 'kd': kd}
                        print(f"  Found better params: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}, "
                              f"rise_time={result['rise_time']:.2f}s, "
                              f"overshoot={result['overshoot']:.2f}%, "
                              f"ss_error={result['steady_state_error']:.3f}")

    if best_params is None:
        # Fallback to reasonable defaults
        print("  No params met all constraints, using reasonable defaults")
        best_params = {'kp': 1.5, 'ki': 0.3, 'kd': 0.5}

    return best_params


def tune_distance_pid():
    """
    Tune distance PID parameters.

    Returns:
        dict: Best PID parameters
    """
    print("\nTuning distance PID parameters...")

    best_params = None
    best_score = float('inf')

    # Search grid - more conservative
    kp_values = np.linspace(0.1, 2.0, 10)
    ki_values = np.linspace(0.0, 0.5, 8)
    kd_values = np.linspace(0.0, 2.0, 10)

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                result = simulate_distance_control(kp, ki, kd)

                # Check constraints including stability
                if result.get('stable', False) and \
                   result['min_distance'] > 5.0 and \
                   result['steady_state_error'] < 2.0 and \
                   result.get('max_speed', 100) < 35.0:

                    # Score: minimize steady-state error while maintaining safe distance
                    score = result['steady_state_error'] + max(0, 5.0 - result['min_distance'])

                    if score < best_score:
                        best_score = score
                        best_params = {'kp': kp, 'ki': ki, 'kd': kd}
                        print(f"  Found better params: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f}, "
                              f"min_dist={result['min_distance']:.2f}m, "
                              f"ss_error={result['steady_state_error']:.3f}m, "
                              f"max_speed={result.get('max_speed', 0):.2f}m/s")

    if best_params is None:
        print("  No params met all constraints, using conservative defaults")
        best_params = {'kp': 0.5, 'ki': 0.0, 'kd': 0.8}

    return best_params


def main():
    """Main tuning function."""
    # Tune speed controller
    speed_params = tune_speed_pid()

    # Tune distance controller
    distance_params = tune_distance_pid()

    # Save results
    results = {
        'pid_speed': {
            'kp': float(speed_params['kp']),
            'ki': float(speed_params['ki']),
            'kd': float(speed_params['kd'])
        },
        'pid_distance': {
            'kp': float(distance_params['kp']),
            'ki': float(distance_params['ki']),
            'kd': float(distance_params['kd'])
        }
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)

    print("\nTuning complete! Results saved to tuning_results.yaml")
    print(f"\nSpeed PID: kp={speed_params['kp']:.3f}, ki={speed_params['ki']:.3f}, kd={speed_params['kd']:.3f}")
    print(f"Distance PID: kp={distance_params['kp']:.3f}, ki={distance_params['ki']:.3f}, kd={distance_params['kd']:.3f}")


if __name__ == '__main__':
    main()

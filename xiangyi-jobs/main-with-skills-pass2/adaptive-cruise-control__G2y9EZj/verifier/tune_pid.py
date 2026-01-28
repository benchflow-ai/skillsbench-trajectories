"""PID Parameter Tuning for ACC System"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_acc(config, sensor_data, dt):
    """Run ACC simulation with given configuration."""
    acc = AdaptiveCruiseControl(config)

    results = []
    ego_speed = 0.0

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0, ego_speed)  # Speed cannot be negative

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error
        })

    return pd.DataFrame(results)


def evaluate_performance(results, set_speed):
    """Evaluate performance metrics."""
    # Find when speed first reaches 90% of set speed (for rise time)
    cruise_data = results[results['mode'] == 'cruise'].copy()

    if len(cruise_data) == 0:
        return None

    # Rise time: time to reach 90% of set speed
    target_90 = 0.9 * set_speed
    rise_idx = cruise_data[cruise_data['ego_speed'] >= target_90].index
    if len(rise_idx) > 0:
        rise_time = cruise_data.loc[rise_idx[0], 'time']
    else:
        rise_time = float('inf')

    # Overshoot: maximum speed above set speed
    max_speed = cruise_data['ego_speed'].max()
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error: average error in final 20s of cruise mode
    final_cruise = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 20]
    if len(final_cruise) > 0:
        steady_state_error = abs(final_cruise['ego_speed'].mean() - set_speed)
    else:
        steady_state_error = float('inf')

    # Distance steady-state error (for follow mode)
    follow_data = results[results['mode'] == 'follow'].copy()
    if len(follow_data) > 0:
        final_follow = follow_data[follow_data['time'] >= follow_data['time'].max() - 20]
        if len(final_follow) > 0:
            distance_ss_error = abs(final_follow['distance_error'].mean())
        else:
            distance_ss_error = 0
    else:
        distance_ss_error = 0

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'steady_state_error': steady_state_error,
        'distance_ss_error': distance_ss_error
    }


def tune_speed_pid(base_config, sensor_data, dt):
    """Tune speed PID controller."""
    print("Tuning speed PID controller...")

    best_params = None
    best_score = float('inf')

    # Grid search for speed controller
    kp_values = np.linspace(1.0, 5.0, 8)
    ki_values = np.linspace(0.05, 0.3, 6)
    kd_values = [1.0, 2.0, 3.0, 4.0]

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                config = base_config.copy()
                config['pid_speed'] = {'kp': kp, 'ki': ki, 'kd': kd}

                results = simulate_acc(config, sensor_data, dt)
                metrics = evaluate_performance(results, config['acc_settings']['set_speed'])

                if metrics is None:
                    continue

                # Score based on requirements
                score = 0
                if metrics['rise_time'] < 10:
                    score += 1
                else:
                    score += metrics['rise_time']

                if metrics['overshoot_pct'] < 5:
                    score += 1
                else:
                    score += metrics['overshoot_pct']

                if metrics['steady_state_error'] < 0.5:
                    score += 1
                else:
                    score += metrics['steady_state_error'] * 10

                if score < best_score:
                    best_score = score
                    best_params = {'kp': kp, 'ki': ki, 'kd': kd}
                    print(f"  kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f} -> "
                          f"rise={metrics['rise_time']:.2f}s, "
                          f"overshoot={metrics['overshoot_pct']:.2f}%, "
                          f"ss_error={metrics['steady_state_error']:.3f} m/s, "
                          f"score={score:.3f}")

    return best_params


def tune_distance_pid(base_config, sensor_data, dt):
    """Tune distance PID controller."""
    print("\nTuning distance PID controller...")

    best_params = None
    best_score = float('inf')

    # Grid search for distance controller
    kp_values = np.linspace(0.3, 2.5, 8)
    ki_values = np.linspace(0.05, 0.4, 6)
    kd_values = [0.5, 1.0, 2.0, 3.0]

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                config = base_config.copy()
                config['pid_distance'] = {'kp': kp, 'ki': ki, 'kd': kd}

                results = simulate_acc(config, sensor_data, dt)
                metrics = evaluate_performance(results, config['acc_settings']['set_speed'])

                if metrics is None:
                    continue

                # Score based on distance control
                score = metrics['distance_ss_error'] * 10

                if score < best_score:
                    best_score = score
                    best_params = {'kp': kp, 'ki': ki, 'kd': kd}
                    print(f"  kp={kp:.3f}, ki={ki:.3f}, kd={kd:.3f} -> "
                          f"distance_error={metrics['distance_ss_error']:.3f} m, "
                          f"score={score:.3f}")

    return best_params


def main():
    # Load configuration and sensor data
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    sensor_data = pd.read_csv('sensor_data.csv')
    dt = base_config['simulation']['dt']

    # Tune speed controller first
    speed_params = tune_speed_pid(base_config, sensor_data, dt)
    base_config['pid_speed'] = speed_params

    # Tune distance controller
    distance_params = tune_distance_pid(base_config, sensor_data, dt)

    # Save tuned parameters
    tuning_results = {
        'pid_speed': speed_params,
        'pid_distance': distance_params
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning complete! Results saved to tuning_results.yaml")
    print(f"Speed PID: kp={speed_params['kp']:.3f}, ki={speed_params['ki']:.3f}, kd={speed_params['kd']:.3f}")
    print(f"Distance PID: kp={distance_params['kp']:.3f}, ki={distance_params['ki']:.3f}, kd={distance_params['kd']:.3f}")


if __name__ == '__main__':
    main()

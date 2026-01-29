"""
Refined PID Parameter Tuning Script

Focus on reducing overshoot while meeting all requirements.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_test_simulation(config):
    """Run a test simulation with given PID parameters."""
    sensor_data = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance
        })

        ego_speed = ego_speed + acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)

    return pd.DataFrame(results)


def calculate_metrics(results_df, config):
    """Calculate performance metrics."""
    set_speed = config['acc_settings']['set_speed']
    metrics = {}

    cruise_data = results_df[results_df['mode'] == 'cruise']

    if len(cruise_data) > 0:
        # Rise time
        target_speed = 0.9 * set_speed
        rise_idx = cruise_data[cruise_data['ego_speed'] >= target_speed].index
        metrics['rise_time'] = cruise_data.loc[rise_idx[0], 'time'] if len(rise_idx) > 0 else 999.0

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        metrics['overshoot_pct'] = ((max_speed - set_speed) / set_speed) * 100

        # Steady-state error
        final_cruise = cruise_data.iloc[int(0.9 * len(cruise_data)):]
        metrics['speed_ss_error'] = abs(final_cruise['ego_speed'].mean() - set_speed) if len(final_cruise) > 0 else 999.0
    else:
        metrics['rise_time'] = 999.0
        metrics['overshoot_pct'] = 0.0
        metrics['speed_ss_error'] = 999.0

    # Distance metrics
    follow_data = results_df[results_df['mode'] == 'follow']
    if len(follow_data) > 0:
        metrics['min_distance'] = follow_data['distance'].min()
        valid_errors = follow_data['distance_error'].dropna()
        if len(valid_errors) > 0:
            final_errors = valid_errors.iloc[int(0.8 * len(valid_errors)):]
            metrics['distance_ss_error'] = abs(final_errors.mean()) if len(final_errors) > 0 else 999.0
        else:
            metrics['distance_ss_error'] = 999.0
    else:
        metrics['min_distance'] = 999.0
        metrics['distance_ss_error'] = 999.0

    return metrics


def tune_pid_parameters():
    """Refined tuning focusing on reducing overshoot."""
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    best_score = -999999
    best_params = None
    best_metrics = None

    print("Starting refined PID parameter tuning...")
    print("Focus: Reduce overshoot while maintaining responsiveness\n")

    # Refined candidates with higher derivative gains to reduce overshoot
    speed_candidates = [
        {'kp': 1.8, 'ki': 0.25, 'kd': 0.5},
        {'kp': 2.0, 'ki': 0.3, 'kd': 0.6},
        {'kp': 1.6, 'ki': 0.2, 'kd': 0.4},
        {'kp': 1.4, 'ki': 0.18, 'kd': 0.35},
        {'kp': 1.7, 'ki': 0.22, 'kd': 0.45},
    ]

    distance_candidates = [
        {'kp': 0.5, 'ki': 0.05, 'kd': 0.2},
        {'kp': 0.4, 'ki': 0.04, 'kd': 0.15},
        {'kp': 0.6, 'ki': 0.06, 'kd': 0.25},
        {'kp': 0.45, 'ki': 0.045, 'kd': 0.18},
    ]

    test_count = 0
    total_tests = len(speed_candidates) * len(distance_candidates)

    for speed_pid in speed_candidates:
        for distance_pid in distance_candidates:
            test_count += 1

            config = base_config.copy()
            config['pid_speed'] = speed_pid
            config['pid_distance'] = distance_pid

            try:
                results_df = run_test_simulation(config)
                metrics = calculate_metrics(results_df, config)

                # Scoring with emphasis on meeting requirements
                score = 0.0

                # Rise time (target < 10s)
                if metrics['rise_time'] < 10.0:
                    score += 2.0 * (1.0 - metrics['rise_time'] / 10.0)

                # Overshoot (target < 5%)
                if metrics['overshoot_pct'] < 5.0:
                    score += 5.0  # High bonus for meeting overshoot
                else:
                    score -= (metrics['overshoot_pct'] - 5.0) * 0.5  # Penalty

                # Speed SS error (target < 0.5 m/s)
                if metrics['speed_ss_error'] < 0.5:
                    score += 2.0

                # Distance SS error (target < 2.0 m)
                if metrics['distance_ss_error'] < 2.0:
                    score += 2.0

                # Min distance (target > 5m)
                if metrics['min_distance'] > 5.0:
                    score += 2.0
                else:
                    score -= 10.0

                print(f"Test {test_count}/{total_tests}:")
                print(f"  Speed: kp={speed_pid['kp']}, ki={speed_pid['ki']}, kd={speed_pid['kd']}")
                print(f"  Distance: kp={distance_pid['kp']}, ki={distance_pid['ki']}, kd={distance_pid['kd']}")
                print(f"  Rise: {metrics['rise_time']:.2f}s, Overshoot: {metrics['overshoot_pct']:.2f}%, "
                      f"Speed SS: {metrics['speed_ss_error']:.3f}, Dist SS: {metrics['distance_ss_error']:.2f}, "
                      f"Min dist: {metrics['min_distance']:.2f}")
                print(f"  Score: {score:.2f}")

                if score > best_score:
                    best_score = score
                    best_params = {'pid_speed': speed_pid, 'pid_distance': distance_pid}
                    best_metrics = metrics
                    print(f"  *** NEW BEST ***")

            except Exception as e:
                print(f"Test {test_count} failed: {e}")

    print("\n" + "="*70)
    print("Refined tuning complete!")
    print("="*70)
    print(f"\nBest Speed PID: kp={best_params['pid_speed']['kp']}, "
          f"ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"Best Distance PID: kp={best_params['pid_distance']['kp']}, "
          f"ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print(f"\nMetrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (< 10s)")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}% (< 5%)")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.3f} m/s (< 0.5)")
    print(f"  Distance SS error: {best_metrics['distance_ss_error']:.2f} m (< 2)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (> 5)")

    return best_params


if __name__ == '__main__':
    best_params = tune_pid_parameters()

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_params, f, default_flow_style=False, sort_keys=False)

    print("\nParameters saved to tuning_results.yaml")

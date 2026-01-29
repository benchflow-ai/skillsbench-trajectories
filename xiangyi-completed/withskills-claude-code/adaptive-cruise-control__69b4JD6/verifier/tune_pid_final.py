"""Final PID tuning with targeted parameter search."""

import yaml
import numpy as np
import pandas as pd
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load configuration from vehicle_params.yaml."""
    with open('vehicle_params.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data():
    """Load sensor data from CSV."""
    return pd.read_csv('sensor_data.csv')


def run_simulation(config, sensor_data):
    """Run simulation with given configuration."""
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    dt = config['simulation']['dt']

    times = []
    speeds = []
    modes = []
    distance_errors = []
    distances = []

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        times.append(time)
        speeds.append(ego_speed)
        modes.append(mode)
        distance_errors.append(dist_error)
        distances.append(distance)

        if idx < len(sensor_data) - 1:
            ego_speed += accel_cmd * dt
            ego_speed = max(0, ego_speed)

    metrics = calculate_metrics(times, speeds, modes, distance_errors, distances, config)
    return metrics


def calculate_metrics(times, speeds, modes, distance_errors, distances, config):
    """Calculate performance metrics."""
    times = np.array(times)
    speeds = np.array(speeds)
    distance_errors = np.array([de if de is not None else np.nan for de in distance_errors])
    distances = np.array([d if d is not None else np.nan for d in distances])

    set_speed = config['acc_settings']['set_speed']
    cruise_indices = [i for i, m in enumerate(modes) if m == 'cruise']

    if len(cruise_indices) > 10:
        speed_10 = 0.1 * set_speed
        speed_90 = 0.9 * set_speed

        idx_10 = np.where(speeds >= speed_10)[0]
        idx_90 = np.where(speeds >= speed_90)[0]

        if len(idx_10) > 0 and len(idx_90) > 0:
            rise_time = times[idx_90[0]] - times[idx_10[0]]
        else:
            rise_time = np.inf

        cruise_speeds = speeds[cruise_indices]
        max_speed = np.max(cruise_speeds)
        overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

        cruise_end_idx = cruise_indices[-1]
        cruise_start_time = times[cruise_indices[0]]
        steady_state_start = cruise_start_time + (times[cruise_end_idx] - cruise_start_time) * 0.8
        steady_indices = [i for i in cruise_indices if times[i] >= steady_state_start]

        if len(steady_indices) > 0:
            steady_speeds = speeds[steady_indices]
            speed_sse = np.mean(np.abs(steady_speeds - set_speed))
        else:
            speed_sse = np.inf
    else:
        rise_time = np.inf
        overshoot_pct = np.inf
        speed_sse = np.inf

    follow_indices = [i for i, m in enumerate(modes) if m == 'follow']

    if len(follow_indices) > 10:
        follow_start_idx = follow_indices[0]
        follow_end_idx = follow_indices[-1]
        steady_start_idx = int(follow_start_idx + 0.2 * (follow_end_idx - follow_start_idx))
        steady_follow_indices = [i for i in follow_indices if i >= steady_start_idx]

        if len(steady_follow_indices) > 0:
            steady_dist_errors = distance_errors[steady_follow_indices]
            distance_sse = np.nanmean(np.abs(steady_dist_errors))
        else:
            distance_sse = np.inf

        follow_distances = distances[follow_indices]
        min_distance = np.nanmin(follow_distances)
    else:
        distance_sse = np.inf
        min_distance = np.inf

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_sse': speed_sse,
        'distance_sse': distance_sse,
        'min_distance': min_distance
    }


def evaluate_pid_params(speed_kp, speed_ki, speed_kd,
                       dist_kp, dist_ki, dist_kd,
                       base_config, sensor_data):
    """Evaluate a set of PID parameters."""
    config = base_config.copy()
    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
    config['pid_distance'] = {'kp': dist_kp, 'ki': dist_ki, 'kd': dist_kd}

    metrics = run_simulation(config, sensor_data)

    constraints_met = (
        metrics['rise_time'] < 10.0 and
        metrics['overshoot_pct'] < 5.0 and
        metrics['speed_sse'] < 0.5 and
        metrics['distance_sse'] < 2.0 and
        metrics['min_distance'] > 5.0
    )

    if constraints_met:
        score = (metrics['rise_time'] +
                metrics['overshoot_pct'] +
                metrics['speed_sse'] +
                metrics['distance_sse'])
    else:
        score = 1000 + (
            max(0, metrics['rise_time'] - 10.0) * 10 +
            max(0, metrics['overshoot_pct'] - 5.0) * 10 +
            max(0, metrics['speed_sse'] - 0.5) * 20 +
            max(0, metrics['distance_sse'] - 2.0) * 20 +
            max(0, 5.0 - metrics['min_distance']) * 50
        )

    return score, metrics, constraints_met


def final_tune():
    """Final tuning with focus on meeting all constraints."""
    print("Loading configuration and sensor data...")
    base_config = load_config()
    sensor_data = load_sensor_data()

    print("Starting final PID parameter tuning...")
    print("Focus: Reduce overshoot (<5%) and improve distance tracking (<2m)\n")

    # Lower kp for speed to reduce overshoot, higher kd for damping
    # Higher kp and kd for distance to improve tracking
    speed_kp_values = [0.8, 1.0, 1.2, 1.4, 1.6]
    speed_ki_values = [0.01, 0.02, 0.03]
    speed_kd_values = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

    dist_kp_values = [1.0, 1.5, 2.0, 2.5, 3.0]
    dist_ki_values = [0.0, 0.01, 0.02, 0.05, 0.1]
    dist_kd_values = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

    best_score = float('inf')
    best_params = None
    best_metrics = None
    best_met_all = False

    iteration = 0
    total = (len(speed_kp_values) * len(speed_ki_values) * len(speed_kd_values) *
             len(dist_kp_values) * len(dist_ki_values) * len(dist_kd_values))

    print(f"Total combinations to test: {total}\n")

    for skp in speed_kp_values:
        for ski in speed_ki_values:
            for skd in speed_kd_values:
                for dkp in dist_kp_values:
                    for dki in dist_ki_values:
                        for dkd in dist_kd_values:
                            iteration += 1

                            score, metrics, met = evaluate_pid_params(
                                skp, ski, skd, dkp, dki, dkd,
                                base_config, sensor_data
                            )

                            # Prioritize solutions that meet all constraints
                            is_better = False
                            if met and not best_met_all:
                                is_better = True
                            elif met and best_met_all and score < best_score:
                                is_better = True
                            elif not met and not best_met_all and score < best_score:
                                is_better = True

                            if is_better:
                                best_score = score
                                best_params = {
                                    'speed': {'kp': skp, 'ki': ski, 'kd': skd},
                                    'distance': {'kp': dkp, 'ki': dki, 'kd': dkd}
                                }
                                best_metrics = metrics
                                best_met_all = met
                                status = "✓ MEETS ALL" if met else "⚠ PARTIAL"
                                print(f"[{iteration}/{total}] New best! {status}")
                                print(f"  Speed PID: ({skp:.2f}, {ski:.3f}, {skd:.2f})")
                                print(f"  Dist PID: ({dkp:.2f}, {dki:.3f}, {dkd:.2f})")
                                print(f"  RT={metrics['rise_time']:.2f}s, "
                                      f"OS={metrics['overshoot_pct']:.2f}%, "
                                      f"SpSSE={metrics['speed_sse']:.3f}m/s, "
                                      f"DistSSE={metrics['distance_sse']:.2f}m, "
                                      f"MinD={metrics['min_distance']:.2f}m")
                                print()

                            if iteration % 200 == 0:
                                print(f"Progress: {iteration}/{total} ({100*iteration/total:.1f}%)")

    print("\n" + "="*70)
    print("FINAL TUNING COMPLETE")
    print("="*70)
    print(f"\nBest Speed PID: kp={best_params['speed']['kp']:.3f}, "
          f"ki={best_params['speed']['ki']:.3f}, kd={best_params['speed']['kd']:.3f}")
    print(f"Best Distance PID: kp={best_params['distance']['kp']:.3f}, "
          f"ki={best_params['distance']['ki']:.3f}, kd={best_params['distance']['kd']:.3f}")

    print(f"\nPerformance Metrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s) "
          f"{'✓' if best_metrics['rise_time'] < 10.0 else '✗'}")
    print(f"  Overshoot: {best_metrics['overshoot_pct']:.2f}% (target: <5%) "
          f"{'✓' if best_metrics['overshoot_pct'] < 5.0 else '✗'}")
    print(f"  Speed SSE: {best_metrics['speed_sse']:.3f} m/s (target: <0.5 m/s) "
          f"{'✓' if best_metrics['speed_sse'] < 0.5 else '✗'}")
    print(f"  Distance SSE: {best_metrics['distance_sse']:.2f} m (target: <2m) "
          f"{'✓' if best_metrics['distance_sse'] < 2.0 else '✗'}")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m) "
          f"{'✓' if best_metrics['min_distance'] > 5.0 else '✗'}")

    if best_met_all:
        print("\n✓ All performance targets met!")
    else:
        print("\n⚠ Some performance targets not met.")

    output = {
        'pid_speed': {
            'kp': float(best_params['speed']['kp']),
            'ki': float(best_params['speed']['ki']),
            'kd': float(best_params['speed']['kd'])
        },
        'pid_distance': {
            'kp': float(best_params['distance']['kp']),
            'ki': float(best_params['distance']['ki']),
            'kd': float(best_params['distance']['kd'])
        }
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(output, f, default_flow_style=False)

    print("\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    final_tune()

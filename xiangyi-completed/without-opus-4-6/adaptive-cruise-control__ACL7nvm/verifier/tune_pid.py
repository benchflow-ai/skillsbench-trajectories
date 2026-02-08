"""PID tuning script - tests parameter combinations and evaluates against performance targets."""

import csv
import yaml

from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_sensor_data(path='sensor_data.csv'):
    """Load sensor data from CSV. Returns list of dicts with time, lead_speed."""
    data = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def run_simulation(config, sensor_data, dt=0.1):
    """Run ACC simulation with simulated ego vehicle and distance tracking.

    The lead vehicle speed comes from sensor_data. The ego vehicle speed and
    distance are simulated based on ACC commands.
    """
    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    distance = None  # No lead vehicle initially
    lead_detected = False
    results = []

    for i, sensor in enumerate(sensor_data):
        lead_speed = sensor['lead_speed']

        # When lead vehicle first appears, initialize distance from sensor data
        if lead_speed is not None and not lead_detected:
            distance = sensor['distance']
            lead_detected = True

        # When lead vehicle disappears
        if lead_speed is None and lead_detected:
            distance = None
            lead_detected = False
            # Reset ACC for cruise mode transition
            acc.speed_controller.reset()
            acc.distance_controller.reset()

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.01 and distance > 0:
                ttc = distance / rel_speed

        results.append({
            'time': sensor['time'],
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel_cmd, 4),
            'mode': mode,
            'distance_error': round(dist_error, 4) if dist_error is not None else None,
            'distance': round(distance, 4) if distance is not None else None,
            'ttc': round(ttc, 4) if ttc is not None else None,
        })

        # Update ego speed
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

        # Update distance if lead vehicle is present
        if lead_speed is not None and distance is not None:
            distance += (lead_speed - ego_speed) * dt
            distance = max(0.0, distance)  # can't go negative

    return results


def evaluate_results(results, set_speed=30.0):
    """Evaluate simulation results against performance targets."""
    metrics = {}

    # Speed rise time: time to reach 90% of set_speed (27 m/s)
    rise_target = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= rise_target:
            rise_time = r['time']
            break
    metrics['rise_time'] = rise_time

    # Speed overshoot: max speed during cruise phases
    cruise_speeds = [r['ego_speed'] for r in results if r['mode'] == 'cruise']
    max_speed = max(cruise_speeds) if cruise_speeds else set_speed
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100.0)
    metrics['overshoot_pct'] = overshoot_pct
    metrics['max_speed'] = max_speed

    # Speed steady-state error in cruise (t=20-29.9, before lead appears)
    cruise_steady = [r['ego_speed'] for r in results if 20.0 <= r['time'] <= 29.9 and r['mode'] == 'cruise']
    if cruise_steady:
        speed_sse = abs(set_speed - sum(cruise_steady) / len(cruise_steady))
    else:
        speed_sse = float('inf')
    metrics['speed_sse'] = speed_sse

    # Also check final cruise (t=140-150)
    final_cruise = [r['ego_speed'] for r in results if 140.0 <= r['time'] <= 150.0 and r['mode'] == 'cruise']
    if final_cruise:
        final_sse = abs(set_speed - sum(final_cruise) / len(final_cruise))
    else:
        final_sse = float('inf')
    metrics['final_speed_sse'] = final_sse

    # Distance steady-state error during stable following (t=40-50s)
    dist_errors = [abs(r['distance_error']) for r in results
                   if r['distance_error'] is not None and 40.0 <= r['time'] <= 50.0]
    if dist_errors:
        dist_sse = sum(dist_errors) / len(dist_errors)
    else:
        dist_sse = float('inf')
    metrics['dist_sse'] = dist_sse

    # Minimum distance during simulation
    distances = [r['distance'] for r in results if r['distance'] is not None]
    min_dist = min(distances) if distances else float('inf')
    metrics['min_distance'] = min_dist

    return metrics


def passes_targets(metrics):
    """Check if all performance targets are met."""
    if metrics['rise_time'] is None or metrics['rise_time'] >= 10.0:
        return False
    if metrics['overshoot_pct'] >= 5.0:
        return False
    if metrics['speed_sse'] >= 0.5:
        return False
    if metrics['dist_sse'] >= 2.0:
        return False
    if metrics['min_distance'] <= 5.0:
        return False
    return True


def main():
    with open('vehicle_params.yaml', 'r') as f:
        base_config = yaml.safe_load(f)

    sensor_data = load_sensor_data()

    # Tuning search space
    speed_candidates = [
        (0.5, 0.02, 0.0),
        (0.6, 0.02, 0.0),
        (0.7, 0.02, 0.0),
        (0.8, 0.02, 0.0),
        (0.8, 0.03, 0.0),
        (0.8, 0.05, 0.0),
        (0.9, 0.02, 0.0),
        (0.9, 0.03, 0.0),
        (1.0, 0.02, 0.0),
        (1.0, 0.03, 0.0),
        (1.0, 0.05, 0.0),
        (1.0, 0.05, 0.1),
        (1.2, 0.03, 0.0),
        (1.2, 0.05, 0.0),
        (1.5, 0.02, 0.0),
        (1.5, 0.03, 0.0),
        (1.5, 0.05, 0.1),
        (2.0, 0.03, 0.0),
        (2.0, 0.05, 0.0),
        (0.8, 0.02, 0.05),
        (0.9, 0.02, 0.05),
        (1.0, 0.02, 0.05),
        (1.0, 0.03, 0.05),
        (1.2, 0.03, 0.05),
        (0.8, 0.05, 0.1),
        (0.9, 0.05, 0.1),
        (1.2, 0.05, 0.1),
        (0.7, 0.03, 0.05),
        (0.7, 0.05, 0.1),
    ]

    distance_candidates = [
        (0.2, 0.005, 0.3),
        (0.2, 0.01, 0.3),
        (0.2, 0.01, 0.5),
        (0.3, 0.005, 0.3),
        (0.3, 0.005, 0.5),
        (0.3, 0.01, 0.3),
        (0.3, 0.01, 0.5),
        (0.3, 0.01, 0.8),
        (0.3, 0.02, 0.5),
        (0.4, 0.005, 0.5),
        (0.4, 0.01, 0.3),
        (0.4, 0.01, 0.5),
        (0.4, 0.01, 0.8),
        (0.4, 0.02, 0.5),
        (0.5, 0.01, 0.5),
        (0.5, 0.01, 0.8),
        (0.5, 0.02, 0.5),
        (0.5, 0.02, 0.8),
        (0.3, 0.01, 1.0),
        (0.4, 0.01, 1.0),
        (0.5, 0.01, 1.0),
        (0.2, 0.005, 0.5),
        (0.25, 0.01, 0.5),
        (0.35, 0.01, 0.5),
        (0.35, 0.01, 0.7),
    ]

    best_score = float('inf')
    best_params = None
    best_metrics = None
    passing_count = 0

    for sp_kp, sp_ki, sp_kd in speed_candidates:
        for dp_kp, dp_ki, dp_kd in distance_candidates:
            config = dict(base_config)
            config['pid_speed'] = {'kp': sp_kp, 'ki': sp_ki, 'kd': sp_kd}
            config['pid_distance'] = {'kp': dp_kp, 'ki': dp_ki, 'kd': dp_kd}

            results = run_simulation(config, sensor_data)
            metrics = evaluate_results(results)

            if not passes_targets(metrics):
                continue

            passing_count += 1

            # Score: weighted combination (lower is better)
            score = (metrics['rise_time'] * 2.0 +
                     metrics['overshoot_pct'] * 5.0 +
                     metrics['speed_sse'] * 10.0 +
                     metrics['dist_sse'] * 5.0 +
                     max(0, 15.0 - metrics['min_distance']) * 2.0)

            if score < best_score:
                best_score = score
                best_params = {
                    'pid_speed': {'kp': sp_kp, 'ki': sp_ki, 'kd': sp_kd},
                    'pid_distance': {'kp': dp_kp, 'ki': dp_ki, 'kd': dp_kd},
                }
                best_metrics = metrics

    print(f"Passing combinations: {passing_count}")

    if best_params is None:
        print("No combination passed all targets. Running diagnostics...")
        # Diagnostic: find best in each metric
        config = dict(base_config)
        config['pid_speed'] = {'kp': 1.0, 'ki': 0.05, 'kd': 0.1}
        config['pid_distance'] = {'kp': 0.3, 'ki': 0.01, 'kd': 0.5}
        results = run_simulation(config, sensor_data)
        metrics = evaluate_results(results)
        print(f"Default metrics: {metrics}")
        best_params = config
        best_metrics = metrics
    else:
        print(f"\nBest parameters found:")
        print(f"  Speed PID: kp={best_params['pid_speed']['kp']}, ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
        print(f"  Distance PID: kp={best_params['pid_distance']['kp']}, ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")

    print(f"\nMetrics:")
    for k, v in best_metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    # Save results
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(best_params, f, default_flow_style=False)

    print(f"\nResults saved to tuning_results.yaml")


if __name__ == '__main__':
    main()

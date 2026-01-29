"""
PID Tuning Script for ACC System

This script tunes the PID parameters for speed and distance control.
Uses a systematic approach to find optimal gains that meet performance targets.
"""

import csv
import yaml
import copy
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    """Load vehicle parameters from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_path: str) -> list:
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })
    return data


def compute_ttc(ego_speed: float, lead_speed: float, distance: float) -> float:
    """Compute Time To Collision."""
    if lead_speed is None or distance is None:
        return float('inf')

    relative_speed = lead_speed - ego_speed
    if relative_speed >= 0:
        return float('inf')

    return distance / abs(relative_speed)


def run_simulation_with_gains(config: dict, sensor_data: list, pid_speed: dict, pid_distance: dict) -> dict:
    """Run simulation with given PID gains and return performance metrics."""
    # Create a copy of config with new gains
    sim_config = copy.deepcopy(config)
    sim_config['pid_speed'] = pid_speed
    sim_config['pid_distance'] = pid_distance

    # Initialize ACC
    acc = AdaptiveCruiseControl(sim_config)

    dt = config['simulation']['dt']
    set_speed = acc.set_speed

    # Simulation state
    ego_speed = 0.0
    min_distance = float('inf')
    max_overshoot = 0.0
    cruise_error_sum = 0.0
    cruise_error_count = 0
    follow_error_sum = 0.0
    follow_error_count = 0
    rise_time = None
    reached_90 = False
    reached_setpoint = False

    # Distance tracking
    distance_errors = []

    for row in sensor_data:
        lead_speed = row['lead_speed']
        distance = row['distance']

        # Compute ACC
        acceleration, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed
        ego_speed = ego_speed + acceleration * dt
        ego_speed = max(0.0, ego_speed)

        # Track rise time (time to reach 90% of set speed)
        if not reached_90 and ego_speed >= 0.9 * set_speed:
            rise_time = row['time']
            reached_90 = True

        # Track overshoot
        if ego_speed > set_speed:
            overshoot = (ego_speed - set_speed) / set_speed * 100
            max_overshoot = max(max_overshoot, overshoot)

        # Track steady-state error in cruise mode (after initial transient, t > 20s, no lead vehicle)
        if row['time'] > 20.0 and mode == 'cruise':
            cruise_error_sum += abs(set_speed - ego_speed)
            cruise_error_count += 1

        # Track error in follow mode (should match lead vehicle speed)
        if mode == 'follow' and lead_speed is not None:
            follow_error_sum += abs(lead_speed - ego_speed)
            follow_error_count += 1

        # Track distance error in follow mode (after initial transient t > 50s)
        if mode == 'follow' and distance is not None and distance_error is not None:
            if row['time'] > 50.0:  # Only measure after controller stabilizes
                distance_errors.append(abs(distance_error))

            # Track minimum distance throughout
            if distance < min_distance:
                min_distance = distance

    # Calculate metrics
    cruise_sse = cruise_error_sum / cruise_error_count if cruise_error_count > 0 else 0
    follow_sse = follow_error_sum / follow_error_count if follow_error_count > 0 else 0
    avg_distance_error = sum(distance_errors) / len(distance_errors) if distance_errors else 0

    return {
        'rise_time': rise_time if rise_time else 999.0,
        'max_overshoot': max_overshoot,
        'cruise_sse': cruise_sse,
        'follow_sse': follow_sse,
        'avg_distance_error': avg_distance_error,
        'min_distance': min_distance if min_distance != float('inf') else None
    }


def tune_speed_pid(config: dict, sensor_data: list) -> dict:
    """Tune PID gains for speed control in cruise mode."""
    print("Tuning speed PID...")

    best_metrics = None
    best_gains = {'kp': 0.5, 'ki': 0.05, 'kd': 0.1}

    # Grid search for speed PID
    kp_values = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    ki_values = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    kd_values = [0.5, 1.0, 2.0, 3.0, 4.0]

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                pid_speed = {'kp': kp, 'ki': ki, 'kd': kd}
                pid_distance = {'kp': 0.1, 'ki': 0.01, 'kd': 0.0}  # Default distance PID

                metrics = run_simulation_with_gains(config, sensor_data, pid_speed, pid_distance)

                # Score based on targets (lower is better)
                score = 0
                score += max(0, metrics['rise_time'] - 10.0) * 10  # Penalty for rise time > 10s
                score += max(0, metrics['max_overshoot'] - 5.0) * 5  # Penalty for overshoot > 5%
                score += max(0, metrics['cruise_sse'] - 0.5) * 10  # Penalty for cruise SSE > 0.5

                if best_metrics is None or score < best_metrics.get('score', float('inf')):
                    best_metrics = {**metrics, 'score': score}
                    best_gains = pid_speed

    print(f"  Best speed PID: kp={best_gains['kp']}, ki={best_gains['ki']}, kd={best_gains['kd']}")
    print(f"  Metrics: rise_time={best_metrics['rise_time']:.2f}s, "
          f"overshoot={best_metrics['max_overshoot']:.2f}%, "
          f"cruise_SSE={best_metrics['cruise_sse']:.4f} m/s")

    return best_gains


def tune_distance_pid(config: dict, sensor_data: list) -> dict:
    """Tune PID gains for distance control in follow mode."""
    print("Tuning distance PID...")

    best_metrics = None
    best_gains = {'kp': 0.5, 'ki': 0.05, 'kd': 0.1}

    # Grid search for distance PID (with tuned speed PID)
    kp_values = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    ki_values = [0.1, 0.2, 0.3, 0.5, 1.0]
    kd_values = [1.0, 2.0, 3.0, 4.0, 5.0]

    tuned_speed = {'kp': 7.0, 'ki': 0.15, 'kd': 4.0}  # Use tuned speed PID

    for kp in kp_values:
        for ki in ki_values:
            for kd in kd_values:
                pid_distance = {'kp': kp, 'ki': ki, 'kd': kd}

                metrics = run_simulation_with_gains(config, sensor_data, tuned_speed, pid_distance)

                # Score based on targets
                score = 0
                if metrics['min_distance'] is not None and metrics['min_distance'] < 5.0:
                    score += 100  # Critical failure

                score += metrics['avg_distance_error'] * 5  # Distance error penalty

                if best_metrics is None or score < best_metrics.get('score', float('inf')):
                    best_metrics = {**metrics, 'score': score}
                    best_gains = pid_distance

    print(f"  Best distance PID: kp={best_gains['kp']}, ki={best_gains['ki']}, kd={best_gains['kd']}")
    print(f"  Metrics: avg_distance_error={best_metrics['avg_distance_error']:.2f}m, "
          f"min_distance={best_metrics['min_distance']:.2f}m")

    return best_gains


def fine_tune(config: dict, sensor_data: list, pid_speed: dict, pid_distance: dict) -> tuple:
    """Fine-tune both PIDs together."""
    print("Fine-tuning both PID controllers...")

    best_gains = (pid_speed, pid_distance)
    best_metrics = None

    # Fine search around initial values
    kp_s_range = [pid_speed['kp'] * x for x in [0.8, 1.0, 1.2]]
    ki_s_range = [pid_speed['ki'] * x for x in [0.5, 1.0, 2.0] if pid_speed['ki'] * x > 0]
    kd_s_range = [max(0, pid_speed['kd'] * x) for x in [0.5, 1.0, 2.0]]

    kp_d_range = [pid_distance['kp'] * x for x in [0.8, 1.0, 1.2]]
    ki_d_range = [pid_distance['ki'] * x if pid_distance['ki'] > 0 else 0.01 for x in [0.5, 1.0, 2.0]]
    kd_d_range = [max(0, pid_distance['kd'] * x) for x in [0.5, 1.0, 2.0]]

    for kps in kp_s_range:
        for kis in ki_s_range:
            for kds in kd_s_range:
                for kpd in kp_d_range:
                    for kid in ki_d_range:
                        for kdd in kd_d_range:
                            ps = {'kp': kps, 'ki': kis, 'kd': kds}
                            pd = {'kp': kpd, 'ki': kid, 'kd': kdd}

                            metrics = run_simulation_with_gains(config, sensor_data, ps, pd)

                            # Calculate comprehensive score
                            score = 0
                            score += max(0, metrics['rise_time'] - 10.0) * 10
                            score += max(0, metrics['max_overshoot'] - 5.0) * 5
                            score += max(0, metrics['cruise_sse'] - 0.5) * 10
                            score += metrics['avg_distance_error'] * 2
                            if metrics['min_distance'] is not None and metrics['min_distance'] < 5.0:
                                score += 50

                            if best_metrics is None or score < best_metrics.get('score', float('inf')):
                                best_metrics = {**metrics, 'score': score}
                                best_gains = (ps, pd)

    return best_gains[0], best_gains[1], best_metrics


def main():
    """Main tuning routine."""
    base_path = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
    config_path = f"{base_path}/vehicle_params.yaml"
    sensor_path = f"{base_path}/sensor_data.csv"
    output_path = f"{base_path}/tuning_results.yaml"

    # Load data
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_path)

    print(f"Loaded {len(sensor_data)} timesteps of sensor data")
    print(f"Set speed: {config['acc_settings']['set_speed']} m/s")

    # Step 1: Tune speed PID
    tuned_speed = tune_speed_pid(config, sensor_data)

    # Step 2: Tune distance PID
    tuned_distance = tune_distance_pid(config, sensor_data)

    # Step 3: Fine-tune both together
    final_speed, final_distance, final_metrics = fine_tune(
        config, sensor_data, tuned_speed, tuned_distance
    )

    print("\n=== Final Tuned Parameters ===")
    print(f"Speed PID: kp={final_speed['kp']:.4f}, ki={final_speed['ki']:.4f}, kd={final_speed['kd']:.4f}")
    print(f"Distance PID: kp={final_distance['kp']:.4f}, ki={final_distance['ki']:.4f}, kd={final_distance['kd']:.4f}")
    print(f"\nPerformance Metrics:")
    print(f"  Rise time: {final_metrics['rise_time']:.2f}s")
    print(f"  Max overshoot: {final_metrics['max_overshoot']:.2f}%")
    print(f"  Cruise SSE: {final_metrics['cruise_sse']:.4f} m/s")
    print(f"  Follow SSE: {final_metrics['follow_sse']:.4f} m/s")
    print(f"  Avg distance error: {final_metrics['avg_distance_error']:.2f} m")
    print(f"  Min distance: {final_metrics['min_distance']:.2f} m")

    # Save results
    tuning_results = {
        'pid_speed': final_speed,
        'pid_distance': final_distance
    }

    with open(output_path, 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print(f"\nTuning results saved to {output_path}")

    return tuning_results


if __name__ == '__main__':
    main()

"""PID Tuning script to find optimal parameters."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str = 'vehicle_params.yaml') -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path: str = 'sensor_data.csv') -> list:
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            lead_speed_str = row.get('lead_speed', '').strip()
            if lead_speed_str == '' or lead_speed_str.lower() == 'none':
                lead_speed = None
            else:
                lead_speed = float(lead_speed_str)
            distance_str = row.get('distance', '').strip()
            if distance_str == '' or distance_str.lower() == 'none':
                distance = None
            else:
                distance = float(distance_str)
            data.append({
                'time': time,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def calculate_ttc(ego_speed: float, lead_speed: float, distance: float) -> float:
    relative_speed = lead_speed - ego_speed
    if relative_speed >= 0:
        return float('inf')
    return abs(distance / relative_speed)


def evaluate_pid(config: dict, sensor_data: list, dt: float) -> dict:
    """Evaluate current PID configuration."""
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    lead_distance = None
    initial_lead_distance = 52.1
    results = []
    min_actual_distance = float('inf')
    max_speed = 0.0
    speed_ss_errors = []
    distance_ss_errors = []
    set_speed = config['acc_settings']['set_speed']
    time_headway = config['acc_settings']['time_headway']
    min_dist_setting = config['acc_settings']['min_distance']

    for row in sensor_data:
        time = row['time']
        lead_speed = row['lead_speed']
        lead_distance_raw = row['distance']

        # Initialize distance when lead vehicle first appears
        if lead_speed is not None and lead_distance is None:
            lead_distance = lead_distance_raw if lead_distance_raw is not None else initial_lead_distance

        # Update lead distance
        if lead_speed is not None:
            if lead_distance_raw is not None:
                lead_distance = lead_distance_raw
            elif lead_distance is not None:
                lead_distance = lead_distance + (lead_speed - ego_speed) * dt
                lead_distance = max(1.0, lead_distance)

        acc_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, lead_distance, dt)

        # Update ego speed
        ego_speed = ego_speed + acc_cmd * dt
        ego_speed = max(0.0, min(ego_speed, set_speed * 1.05))

        if lead_speed is not None and lead_distance is not None and lead_distance > 0:
            ttc = calculate_ttc(ego_speed, lead_speed, lead_distance)
        else:
            ttc = None

        if lead_distance is not None:
            min_actual_distance = min(min_actual_distance, lead_distance)
        max_speed = max(max_speed, ego_speed)

        results.append({'time': time, 'ego_speed': ego_speed, 'mode': mode})

        # Steady state analysis (after lead vehicle appears)
        if time >= 30.0:
            # Speed error: only in cruise mode (no lead vehicle)
            if lead_speed is None:
                speed_ss_errors.append(abs(set_speed - ego_speed))
            # Distance error: only when we're too close (actual < desired) and distance < 70m
            if lead_speed is not None and lead_distance is not None and lead_distance < 70.0:
                desired_dist = min_dist_setting + ego_speed * time_headway
                # Only penalize if we're too close (positive error means we need more distance)
                if lead_distance < desired_dist:
                    distance_ss_errors.append(desired_dist - lead_distance)

    # Calculate metrics
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    overshoot = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0.0
    speed_ss_error = max(speed_ss_errors) if speed_ss_errors else 0.0
    distance_ss_error = max(distance_ss_errors) if distance_ss_errors else 0.0

    return {
        'rise_time': rise_time,
        'max_speed': max_speed,
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_actual_distance if min_actual_distance != float('inf') else None
    }


def grid_search():
    """Simple grid search for PID tuning."""
    config = load_config()
    sensor_data = load_sensor_data()
    dt = config['simulation']['dt']

    best_params = None
    best_score = float('inf')

    # Search range based on requirements
    kp_range = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ki_range = [0.05, 0.1, 0.2, 0.3, 0.5]
    kd_range = [0.5, 1.0, 1.5, 2.0, 2.5]

    print("Tuning PID parameters...")
    total = len(kp_range) * len(ki_range) * len(kd_range)
    count = 0

    for kp in kp_range:
        for ki in ki_range:
            for kd in kd_range:
                count += 1
                # Update speed PID
                config['pid_speed']['kp'] = kp
                config['pid_speed']['ki'] = ki
                config['pid_speed']['kd'] = kd

                # Distance PID with scaled gains
                config['pid_distance']['kp'] = kp * 0.2
                config['pid_distance']['ki'] = ki * 0.1
                config['pid_distance']['kd'] = kd * 0.3

                metrics = evaluate_pid(config, sensor_data, dt)

                # Calculate score (lower is better)
                # Targets: rise_time < 10s, overshoot < 5%, speed_ss_error < 0.5, dist_ss_error < 2, min_dist > 5
                score = 0

                if metrics['rise_time'] and metrics['rise_time'] > 10:
                    score += (metrics['rise_time'] - 10) * 50
                elif metrics['rise_time']:
                    score += (10 - metrics['rise_time']) * 5

                if metrics['overshoot'] > 5:
                    score += (metrics['overshoot'] - 5) * 20

                score += metrics['speed_ss_error'] * 100
                score += metrics['distance_ss_error'] * 20

                if metrics['min_distance'] and metrics['min_distance'] < 5:
                    score += (5 - metrics['min_distance']) * 50

                if score < best_score:
                    best_score = score
                    best_params = {
                        'pid_speed': {'kp': kp, 'ki': ki, 'kd': kd},
                        'pid_distance': {
                            'kp': kp * 0.2,
                            'ki': ki * 0.1,
                            'kd': kd * 0.3
                        }
                    }

                print(f"\rProgress: {count}/{total}", end='', flush=True)

    print(f"\n\nBest parameters found:")
    print(f"  Speed PID: kp={best_params['pid_speed']['kp']}, ki={best_params['pid_speed']['ki']}, kd={best_params['pid_speed']['kd']}")
    print(f"  Distance PID: kp={best_params['pid_distance']['kp']}, ki={best_params['pid_distance']['ki']}, kd={best_params['pid_distance']['kd']}")
    print(f"  Score: {best_score:.4f}")

    return best_params


if __name__ == '__main__':
    params = grid_search()
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(params, f, default_flow_style=False)
    print("\nSaved to tuning_results.yaml")

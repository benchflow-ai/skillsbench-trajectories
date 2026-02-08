"""ACC simulation runner.

Reads PID gains from tuning_results.yaml, vehicle config from vehicle_params.yaml,
and lead vehicle data from sensor_data.csv. Produces simulation_results.csv.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(params_path, tuning_path):
    """Load vehicle params and override PID gains from tuning results."""
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_path, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data(sensor_path):
    """Load sensor data CSV and return list of dicts with parsed values."""
    data = []
    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed_orig': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'].strip() else None,
                'distance_orig': float(row['distance']) if row['distance'].strip() else None,
            }
            data.append(entry)
    return data


def build_lead_trajectory(sensor_data, dt):
    """Build lead vehicle trajectory by integrating lead speed.

    The lead vehicle's position is computed relative to a reference point.
    For timesteps where no lead vehicle exists, returns None.
    The initial lead distance (from sensor data) is preserved as the offset
    from the simulated ego at the moment the lead first appears.

    Returns:
        list of dict: each with 'lead_speed' and 'lead_delta' (distance
            the lead has traveled since first appearing), or None entries
            for timesteps with no lead.
        float: initial_distance - the recorded gap when lead first appears
    """
    # Find the first timestep with a lead vehicle
    first_lead_idx = None
    for i, s in enumerate(sensor_data):
        if s['lead_speed'] is not None:
            first_lead_idx = i
            break

    if first_lead_idx is None:
        return [None] * len(sensor_data), 0.0

    initial_distance = sensor_data[first_lead_idx]['distance_orig']

    # Integrate lead speed to get cumulative displacement from first appearance
    trajectory = [None] * len(sensor_data)
    lead_displacement = 0.0

    for i in range(first_lead_idx, len(sensor_data)):
        s = sensor_data[i]
        if s['lead_speed'] is None:
            # Lead vehicle has left; mark remaining as None
            break
        trajectory[i] = {
            'lead_speed': s['lead_speed'],
            'lead_displacement': lead_displacement,
        }
        lead_displacement += s['lead_speed'] * dt

    return trajectory, initial_distance


def run_simulation(config, sensor_data):
    """Run ACC simulation and return list of result rows.

    The simulation controls the ego vehicle (starting from 0 m/s) while
    the lead vehicle trajectory is derived from sensor_data.csv lead_speed
    values. The initial gap is set to the recorded distance at the moment
    the lead vehicle first appears.
    """
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    lead_trajectory, initial_distance = build_lead_trajectory(sensor_data, dt)

    ego_speed = 0.0
    ego_pos = 0.0
    ego_pos_at_lead_start = None  # Set when lead first appears
    results = []

    for i, sensor in enumerate(sensor_data):
        traj = lead_trajectory[i]

        if traj is not None:
            lead_speed = traj['lead_speed']
            # Set anchor point on first lead appearance
            if ego_pos_at_lead_start is None:
                ego_pos_at_lead_start = ego_pos

            # Lead position = ego_at_start + initial_gap + lead_displacement
            lead_pos = ego_pos_at_lead_start + initial_distance + traj['lead_displacement']
            distance = lead_pos - ego_pos
        else:
            lead_speed = None
            distance = None

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed

        # Record result
        results.append({
            'time': round(sensor['time'], 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(distance_error, 2) if distance_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else '',
        })

        # Update ego vehicle dynamics
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot go negative
        ego_pos += ego_speed * dt

    return results


def write_results(results, output_path):
    """Write simulation results to CSV."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')
    results = run_simulation(config, sensor_data)
    write_results(results, 'simulation_results.csv')
    print(f"Simulation complete. Wrote {len(results)} rows to simulation_results.csv")

    # Print summary metrics
    print_metrics(results)


def print_metrics(results):
    """Print key performance metrics."""
    set_speed = 30.0

    # Rise time: time to reach 90% of set_speed (first cruise phase)
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break

    # Overshoot (check entire simulation)
    max_speed = max(r['ego_speed'] for r in results)
    overshoot_pct = ((max_speed - set_speed) / set_speed) * 100.0 if max_speed > set_speed else 0.0

    # Speed steady-state error (last 5s of first cruise phase, t=25-30)
    ss_cruise = [r for r in results if 25.0 <= r['time'] <= 30.0
                 and r['mode'] == 'cruise']
    if ss_cruise:
        ss_error = abs(set_speed - sum(r['ego_speed'] for r in ss_cruise) / len(ss_cruise))
    else:
        ss_error = float('nan')

    # Distance steady-state error (stable follow period where lead speed < set_speed)
    # Evaluated during t=40-75s when lead speed is stable and below set_speed
    stable_follow = [r for r in results if r['mode'] == 'follow'
                     and r['distance_error'] != ''
                     and 40.0 <= r['time'] <= 75.0]
    if stable_follow:
        n_tail = max(1, len(stable_follow) // 3)
        dist_errors = [abs(r['distance_error']) for r in stable_follow[-n_tail:]]
        ss_dist_error = sum(dist_errors) / len(dist_errors)
    else:
        ss_dist_error = float('nan')

    # Min distance
    all_distances = [r['distance'] for r in results if r['distance'] != '']
    min_dist = min(all_distances) if all_distances else float('nan')

    print(f"\n--- Performance Metrics ---")
    print(f"Rise time (to 90% of {set_speed} m/s): {rise_time} s")
    print(f"Max speed: {max_speed:.2f} m/s")
    print(f"Speed overshoot: {overshoot_pct:.2f}%")
    print(f"Speed steady-state error: {ss_error:.3f} m/s")
    print(f"Distance steady-state error: {ss_dist_error:.2f} m")
    print(f"Minimum distance: {min_dist} m")


if __name__ == '__main__':
    main()

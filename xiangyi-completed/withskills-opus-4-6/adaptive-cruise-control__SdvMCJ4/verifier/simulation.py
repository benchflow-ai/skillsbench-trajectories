"""Run 150-second ACC simulation using sensor_data.csv for lead vehicle data.

Reads PID gains from tuning_results.yaml and vehicle config from vehicle_params.yaml.
Uses lead_speed from sensor_data.csv as lead vehicle input.
Simulates ego speed via PID-controlled acceleration and distance via kinematics.
Produces simulation_results.csv with columns:
    time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc
"""

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(path):
    """Load sensor_data.csv into a dict keyed by rounded time.

    Returns lead_speed and initial_distance (from CSV) for each timestep.
    """
    data = {}
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = round(float(row['time']), 1)
            lead_speed = float(row['lead_speed']) if row['lead_speed'].strip() else None
            distance = float(row['distance']) if row['distance'].strip() else None
            data[t] = {'lead_speed': lead_speed, 'csv_distance': distance}
    return data


def run_simulation():
    # Load configurations
    vehicle_config = load_yaml('vehicle_params.yaml')
    tuning = load_yaml('tuning_results.yaml')

    # Override PID gains with tuned values
    vehicle_config['pid_speed'] = tuning['pid_speed']
    vehicle_config['pid_distance'] = tuning['pid_distance']

    # Load sensor data for lead vehicle behaviour
    sensor_data = load_sensor_data('sensor_data.csv')

    dt = vehicle_config['simulation']['dt']

    # Create ACC controller
    acc = AdaptiveCruiseControl(vehicle_config)

    # Simulation state
    ego_speed = 0.0
    sim_distance = None  # Simulated gap to lead vehicle
    lead_present_prev = False  # Track transitions
    results = []

    num_steps = 1501  # t = 0.0 to 150.0 at dt=0.1

    for step in range(num_steps):
        t = round(step * dt, 1)

        # Look up lead vehicle data from sensor CSV
        sensor = sensor_data.get(t, {'lead_speed': None, 'csv_distance': None})
        lead_speed = sensor['lead_speed']
        csv_distance = sensor['csv_distance']

        lead_present = lead_speed is not None

        # Manage simulated distance
        if lead_present and not lead_present_prev:
            # Lead vehicle just appeared — initialize distance from CSV
            sim_distance = csv_distance
        elif not lead_present:
            sim_distance = None

        # Compute ACC command using simulated distance
        accel_cmd, mode, dist_error = acc.compute(
            ego_speed, lead_speed, sim_distance, dt
        )

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and sim_distance is not None and sim_distance > 0:
            closing = ego_speed - lead_speed
            if closing > 0:
                ttc = sim_distance / closing

        # Record result
        results.append({
            'time': f'{t:.1f}',
            'ego_speed': f'{round(ego_speed, 2)}',
            'acceleration_cmd': f'{round(accel_cmd, 2)}',
            'mode': mode,
            'distance_error': f'{round(dist_error, 2)}' if dist_error is not None else '',
            'distance': f'{round(sim_distance, 2)}' if sim_distance is not None else '',
            'ttc': f'{round(ttc, 2)}' if ttc is not None else '',
        })

        # Update ego speed (kinematics)
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # speed cannot be negative

        # Update simulated distance
        if lead_present and sim_distance is not None:
            sim_distance = sim_distance - (ego_speed - lead_speed) * dt
            sim_distance = max(0.0, sim_distance)  # cannot be negative

        lead_present_prev = lead_present

    # Write results CSV
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f'Wrote {len(results)} rows to simulation_results.csv')
    return results


def compute_metrics(results):
    """Compute and print performance metrics from simulation results."""
    # --- Speed rise time (time to reach 90% of set_speed=30 from 0) ---
    target_90 = 30.0 * 0.9  # 27.0 m/s
    rise_time = None
    for r in results:
        if float(r['ego_speed']) >= target_90:
            rise_time = float(r['time'])
            break

    # --- Speed overshoot (in cruise phases: t=0-30 and t=130-150) ---
    max_speed = 0.0
    for r in results:
        t = float(r['time'])
        if t <= 30.0 or t >= 130.0:
            s = float(r['ego_speed'])
            if s > max_speed:
                max_speed = s
    overshoot_pct = ((max_speed - 30.0) / 30.0) * 100.0 if max_speed > 30.0 else 0.0

    # --- Speed steady-state error (last 5s of initial cruise: t=25-30) ---
    cruise_errors = []
    for r in results:
        t = float(r['time'])
        if 25.0 <= t <= 29.9:
            cruise_errors.append(abs(30.0 - float(r['ego_speed'])))
    speed_ss_error = sum(cruise_errors) / len(cruise_errors) if cruise_errors else 0.0

    # --- Distance steady-state error (during stable follow, t=40-50) ---
    dist_errors = []
    for r in results:
        t = float(r['time'])
        if 40.0 <= t <= 50.0 and r['distance_error']:
            dist_errors.append(abs(float(r['distance_error'])))
    dist_ss_error = sum(dist_errors) / len(dist_errors) if dist_errors else 0.0

    # --- Minimum distance (entire simulation when lead present) ---
    min_dist = float('inf')
    for r in results:
        if r['distance']:
            d = float(r['distance'])
            if d < min_dist:
                min_dist = d
    if min_dist == float('inf'):
        min_dist = None

    print('\n=== Performance Metrics ===')
    print(f'Speed rise time (to 90%):  {rise_time:.1f}s  (target: <10s)')
    print(f'Speed overshoot:           {overshoot_pct:.2f}%  (target: <5%)')
    print(f'Speed steady-state error:  {speed_ss_error:.3f} m/s  (target: <0.5 m/s)')
    print(f'Distance steady-state err: {dist_ss_error:.3f} m  (target: <2m)')
    if min_dist is not None:
        print(f'Minimum distance:          {min_dist:.2f} m  (target: >5m)')
    else:
        print(f'Minimum distance:          N/A')
    print(f'Control duration:          150.0s')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_dist': min_dist,
    }


if __name__ == '__main__':
    results = run_simulation()
    compute_metrics(results)

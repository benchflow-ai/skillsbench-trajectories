"""
Main simulation script for Adaptive Cruise Control system.
Reads PID gains from tuning_results.yaml and runs 150s simulation.
Simulates ego vehicle dynamics based on ACC commands.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and PID tuning results."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Override PID gains from tuning results
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed']['kp'] = tuning['pid_speed']['kp']
            config['pid_speed']['ki'] = tuning['pid_speed']['ki']
            config['pid_speed']['kd'] = tuning['pid_speed']['kd']
            config['pid_distance']['kp'] = tuning['pid_distance']['kp']
            config['pid_distance']['ki'] = tuning['pid_distance']['ki']
            config['pid_distance']['kd'] = tuning['pid_distance']['kd']
    except FileNotFoundError:
        pass

    return config


def load_sensor_data():
    """Load sensor data from CSV file."""
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data


def run_simulation():
    """Run the ACC simulation with ego vehicle dynamics."""
    config = load_config()
    acc = AdaptiveCruiseControl(config)

    sensor_data = load_sensor_data()

    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    results = []

    # Initialize ego vehicle state
    ego_speed = 0.0
    ego_position = 0.0

    # Lead vehicle state
    lead_position = None
    prev_lead_speed = None

    for i, data in enumerate(sensor_data):
        time = data['time']
        measured_lead_speed = data['lead_speed']
        measured_distance = data['distance']

        # Check if lead vehicle data ended (became None after being valid)
        if measured_lead_speed is None and lead_position is not None:
            # Lead vehicle lost - clear tracking
            lead_position = None

        # Update lead vehicle position
        if measured_lead_speed is not None:
            if lead_position is None:
                # First detection - initialize position
                if measured_distance is not None:
                    lead_position = ego_position + measured_distance
            else:
                # Update position based on measured lead speed
                lead_position += measured_lead_speed * dt

        # Get measured distance for ACC
        acc_distance = None
        if lead_position is not None and ego_position is not None:
            acc_distance = lead_position - ego_position

        # Get acceleration command from ACC
        acc_cmd, mode, distance_error = acc.compute(
            ego_speed, measured_lead_speed, acc_distance, dt
        )

        # Apply acceleration limits
        acc_cmd = max(max_decel, min(max_accel, acc_cmd))

        # Update ego vehicle dynamics
        ego_speed += acc_cmd * dt
        ego_speed = max(0, ego_speed)
        ego_position += ego_speed * dt

        # Calculate TTC
        ttc = float('inf')
        if acc_distance is not None and acc_distance > 0 and measured_lead_speed is not None:
            relative_speed = measured_lead_speed - ego_speed
            if relative_speed < 0 and acc_distance > 0:
                ttc = acc_distance / (-relative_speed)

        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': acc_distance if acc_distance is not None else '',
            'ttc': ttc if ttc != float('inf') else ''
        })

    return results


def write_results(results):
    """Write simulation results to CSV file."""
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == '__main__':
    results = run_simulation()
    write_results(results)
    print(f"Simulation complete. {len(results)} rows written to simulation_results.csv")

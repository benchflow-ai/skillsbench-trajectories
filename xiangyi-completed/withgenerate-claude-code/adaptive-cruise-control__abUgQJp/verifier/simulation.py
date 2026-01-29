"""ACC Simulation module.

Runs vehicle simulation using sensor data and ACC system.
Reads PID gains from tuning_results.yaml at runtime.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(filepath: str) -> dict:
    """Load configuration from YAML file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath: str) -> list:
    """
    Load sensor data from CSV file.

    Args:
        filepath: Path to sensor_data.csv

    Returns:
        List of dictionaries with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']) if row['ego_speed'] else None,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def run_simulation(acc: AdaptiveCruiseControl, sensor_data: list,
                   dt: float = 0.1) -> list:
    """
    Run ACC simulation.

    The simulation uses lead_speed from sensor_data but computes its own
    ego_speed and distance. When a lead vehicle appears, the initial distance
    is taken from sensor_data. Subsequently, distance is updated based on
    relative velocities.

    Args:
        acc: Configured AdaptiveCruiseControl instance
        sensor_data: List of sensor readings from sensor_data.csv
        dt: Timestep in seconds

    Returns:
        List of result dictionaries
    """
    # Initialize ego vehicle state
    ego_speed = 0.0
    distance = None  # Our computed distance to lead vehicle
    prev_had_lead = False
    results = []

    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']

        # Handle distance tracking
        if lead_speed is not None and sensor_distance is not None:
            if not prev_had_lead:
                # Lead vehicle just appeared - use initial distance from sensor
                distance = sensor_distance
            else:
                # Update distance based on relative velocity
                # distance changes by (lead_speed - ego_speed) * dt
                distance += (lead_speed - ego_speed) * dt
                distance = max(0.0, distance)  # Can't be negative
            prev_had_lead = True
        else:
            # No lead vehicle
            distance = None
            prev_had_lead = False

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed

        # Log results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego vehicle state using simple Euler integration
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Cannot go backwards

    return results


def save_results(results: list, filepath: str):
    """
    Save simulation results to CSV.

    Args:
        results: List of result dictionaries
        filepath: Output file path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)

        for row in results:
            formatted_row = []
            for field in fieldnames:
                value = row.get(field)
                if value is None:
                    formatted_row.append('')
                elif isinstance(value, float):
                    # Format floats with reasonable precision
                    formatted_row.append(f'{value:.6g}')
                else:
                    formatted_row.append(str(value))
            writer.writerow(formatted_row)


def main():
    """Main simulation entry point."""
    # Load vehicle configuration
    vehicle_config = load_config('vehicle_params.yaml')

    # Load PID tuning results
    tuning = load_config('tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Get timestep from config
    dt = vehicle_config.get('simulation', {}).get('dt', 0.1)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(vehicle_config)

    # Set PID controllers from tuning results
    acc.set_speed_controller(
        kp=tuning['pid_speed']['kp'],
        ki=tuning['pid_speed']['ki'],
        kd=tuning['pid_speed']['kd']
    )
    acc.set_distance_controller(
        kp=tuning['pid_distance']['kp'],
        ki=tuning['pid_distance']['ki'],
        kd=tuning['pid_distance']['kd']
    )

    # Run simulation
    results = run_simulation(acc, sensor_data, dt)

    # Save results
    save_results(results, 'simulation_results.csv')

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")


if __name__ == '__main__':
    main()

"""ACC System Simulation using real-world sensor data."""

import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """
    Run ACC simulation using sensor data and tuned PID parameters.

    Reads:
    - vehicle_params.yaml: Vehicle and ACC configuration
    - tuning_results.yaml: Tuned PID parameters
    - sensor_data.csv: Lead vehicle data (time, ego_speed, lead_speed, distance)

    Writes:
    - simulation_results.csv: Simulation results with exact format
    """
    # Load vehicle parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Update config with tuned parameters
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    # Load sensor data
    sensor_df = pd.read_csv('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Initialize state
    ego_speed = 0.0  # Start from rest
    results = []

    # Main simulation loop
    for idx, row in sensor_df.iterrows():
        time = row['time']

        # Get lead vehicle data (may be NaN/None)
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute control
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC if applicable
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results before updating state
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        }
        results.append(result)

        # Update ego vehicle state
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Cannot go backwards

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Save to CSV with exact column order
    results_df.to_csv('simulation_results.csv', index=False)

    print(f"Simulation completed: {len(results)} timesteps")
    print(f"Results saved to simulation_results.csv")

    return results_df


if __name__ == '__main__':
    run_simulation()

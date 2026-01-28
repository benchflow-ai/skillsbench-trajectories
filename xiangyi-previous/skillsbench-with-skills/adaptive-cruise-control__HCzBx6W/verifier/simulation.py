"""Run ACC simulation using sensor data and tuned PID parameters."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def calculate_ttc(ego_speed, lead_speed, distance):
    """
    Calculate time-to-collision.

    Args:
        ego_speed: Ego vehicle speed (m/s)
        lead_speed: Lead vehicle speed (m/s)
        distance: Distance to lead vehicle (m)

    Returns:
        float or None: TTC in seconds, or None if not applicable
    """
    if lead_speed is None or distance is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed > 0:
        return distance / relative_speed
    return None


def run_simulation():
    """Run the ACC simulation for 150 seconds."""
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Override config with tuned parameters
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_acceleration = config['vehicle']['max_acceleration']
    max_deceleration = config['vehicle']['max_deceleration']

    # Initialize simulation state
    ego_speed = 0.0

    # Results storage
    results = []

    # Run simulation
    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command and mode
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

        # Store results for current timestep
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        }
        results.append(result)

        # Update ego speed for next iteration
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)  # Don't go negative

    # Create results dataframe
    results_df = pd.DataFrame(results)

    # Save results
    results_df.to_csv('simulation_results.csv', index=False)

    print(f"Simulation complete. Processed {len(results)} timesteps.")
    print(f"Results saved to simulation_results.csv")

    # Calculate and print performance metrics
    print_performance_metrics(results_df, config)


def print_performance_metrics(results_df, config):
    """Print performance metrics from simulation results."""
    set_speed = config['acc_settings']['set_speed']

    print("\n=== Performance Metrics ===")

    # Speed metrics (cruise mode only)
    cruise_data = results_df[results_df['mode'] == 'cruise']

    if len(cruise_data) > 0:
        # Rise time: time to reach 90% of set speed
        target_90 = 0.9 * set_speed
        rise_data = cruise_data[cruise_data['ego_speed'] >= target_90]
        if len(rise_data) > 0:
            rise_time = rise_data.iloc[0]['time']
            print(f"Rise time: {rise_time:.2f}s (target: <10s)")
        else:
            print("Rise time: Not achieved")

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
        print(f"Overshoot: {overshoot_pct:.2f}% (target: <5%)")

        # Steady-state error (last 20% of cruise mode)
        last_20_pct = int(len(cruise_data) * 0.8)
        steady_state_data = cruise_data.iloc[last_20_pct:]
        if len(steady_state_data) > 0:
            ss_error_speed = abs(steady_state_data['ego_speed'] - set_speed).mean()
            print(f"Speed steady-state error: {ss_error_speed:.3f} m/s (target: <0.5 m/s)")

    # Distance metrics (follow mode)
    follow_data = results_df[results_df['mode'].isin(['follow', 'emergency'])]

    if len(follow_data) > 0:
        # Filter out empty distance_error values
        follow_with_error = follow_data[follow_data['distance_error'] != '']

        if len(follow_with_error) > 0:
            # Steady-state error (last 20% of follow mode)
            last_20_pct = int(len(follow_with_error) * 0.8)
            steady_state_data = follow_with_error.iloc[last_20_pct:]
            if len(steady_state_data) > 0:
                ss_error_distance = abs(steady_state_data['distance_error']).mean()
                print(f"Distance steady-state error: {ss_error_distance:.2f}m (target: <2m)")

        # Minimum distance
        distance_data = follow_data[follow_data['distance'] != '']
        if len(distance_data) > 0:
            min_distance = distance_data['distance'].min()
            print(f"Minimum distance: {min_distance:.2f}m (target: >5m)")

    print(f"\nTotal simulation duration: {results_df['time'].max():.1f}s")


if __name__ == '__main__':
    run_simulation()

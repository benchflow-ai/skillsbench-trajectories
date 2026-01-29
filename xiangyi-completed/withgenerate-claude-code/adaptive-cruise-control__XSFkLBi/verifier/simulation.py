"""
ACC Simulation Runner

This script runs the complete ACC simulation using sensor data and tuned PID parameters.
It loads configuration from YAML files, processes sensor data, runs the simulation,
and generates output files.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_config():
    """
    Load vehicle parameters and PID gains.

    Returns:
        dict: Combined configuration with vehicle params and tuned PID gains
    """
    # Load base configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID parameters with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data():
    """
    Load sensor data from CSV file.

    Returns:
        pd.DataFrame: Sensor data with columns [time, ego_speed, lead_speed, distance]
    """
    df = pd.read_csv('sensor_data.csv')
    return df


def calculate_ttc(ego_speed, lead_speed, distance):
    """
    Calculate time-to-collision.

    Args:
        ego_speed (float): Ego vehicle speed in m/s
        lead_speed (float or None): Lead vehicle speed in m/s
        distance (float or None): Distance to lead vehicle in meters

    Returns:
        float or None: TTC in seconds, or None if not applicable
    """
    if lead_speed is None or distance is None:
        return None

    relative_speed = ego_speed - lead_speed

    if relative_speed > 0 and distance > 0:
        # Approaching lead vehicle
        ttc = distance / relative_speed
        return ttc
    else:
        # Not approaching or invalid
        return None


def run_simulation():
    """
    Run the complete ACC simulation.

    Returns:
        pd.DataFrame: Simulation results
    """
    # Load configuration and data
    config = load_config()
    sensor_data = load_sensor_data()

    # Extract simulation parameters
    dt = config['simulation']['dt']
    max_acceleration = config['vehicle']['max_acceleration']
    max_deceleration = config['vehicle']['max_deceleration']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize simulation state
    ego_speed = 0.0
    results = []

    # Simulation loop
    for idx, row in sensor_data.iterrows():
        time = row['time']

        # Get lead vehicle data (handle missing values)
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute control command
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

        # Record results BEFORE updating speed
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego vehicle speed (simple Euler integration)
        ego_speed = ego_speed + acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot be negative

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    return results_df


def save_results(results_df):
    """
    Save simulation results to CSV file.

    Args:
        results_df (pd.DataFrame): Simulation results
    """
    # Ensure column order matches expected format
    columns = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
               'distance_error', 'distance', 'ttc']

    results_df = results_df[columns]

    # Save to CSV
    results_df.to_csv('simulation_results.csv', index=False)

    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total rows: {len(results_df)}")


def print_performance_metrics(results_df, config):
    """
    Calculate and print key performance metrics.

    Args:
        results_df (pd.DataFrame): Simulation results
        config (dict): Configuration parameters
    """
    set_speed = config['acc_settings']['set_speed']

    # Speed control metrics (cruise mode)
    cruise_data = results_df[results_df['mode'] == 'cruise']

    if len(cruise_data) > 0:
        # Rise time (time to reach 90% of set speed)
        target_speed = 0.9 * set_speed
        rise_idx = cruise_data[cruise_data['ego_speed'] >= target_speed].index
        if len(rise_idx) > 0:
            rise_time = cruise_data.loc[rise_idx[0], 'time']
            print(f"\nSpeed Rise Time: {rise_time:.2f} s (target: <10s)")

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot = ((max_speed - set_speed) / set_speed) * 100
        print(f"Speed Overshoot: {overshoot:.2f}% (target: <5%)")

        # Steady-state error (final 10% of cruise mode)
        final_cruise = cruise_data.iloc[int(0.9 * len(cruise_data)):]
        if len(final_cruise) > 0:
            ss_error = abs(final_cruise['ego_speed'].mean() - set_speed)
            print(f"Speed Steady-State Error: {ss_error:.3f} m/s (target: <0.5 m/s)")

    # Distance control metrics (follow mode)
    follow_data = results_df[results_df['mode'] == 'follow']

    if len(follow_data) > 0:
        # Minimum distance
        min_distance = follow_data['distance'].min()
        print(f"\nMinimum Distance: {min_distance:.2f} m (target: >5m)")

        # Distance steady-state error
        valid_errors = follow_data['distance_error'].dropna()
        if len(valid_errors) > 0:
            final_errors = valid_errors.iloc[int(0.8 * len(valid_errors)):]
            if len(final_errors) > 0:
                ss_dist_error = abs(final_errors.mean())
                print(f"Distance Steady-State Error: {ss_dist_error:.2f} m (target: <2m)")

    # Mode distribution
    print("\nMode Distribution:")
    mode_counts = results_df['mode'].value_counts()
    for mode, count in mode_counts.items():
        percentage = (count / len(results_df)) * 100
        print(f"  {mode}: {count} steps ({percentage:.1f}%)")


if __name__ == '__main__':
    # Run simulation
    results_df = run_simulation()

    # Save results
    save_results(results_df)

    # Load config for metrics
    config = load_config()

    # Print performance metrics
    print_performance_metrics(results_df, config)

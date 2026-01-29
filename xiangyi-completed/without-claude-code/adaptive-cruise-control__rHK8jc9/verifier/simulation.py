"""ACC System Simulation"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """
    Run the ACC simulation for 150 seconds.

    Loads PID gains from tuning_results.yaml and sensor data from sensor_data.csv.
    Produces simulation_results.csv with the complete simulation results.
    """
    print("=" * 60)
    print("ACC System Simulation")
    print("=" * 60)

    # Load vehicle parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains
    print("\nLoading PID gains from tuning_results.yaml...")
    with open('tuning_results.yaml', 'r') as f:
        tuning_results = yaml.safe_load(f)

    # Update config with tuned PID parameters
    config['pid_speed'] = tuning_results['pid_speed']
    config['pid_distance'] = tuning_results['pid_distance']

    print(f"Speed PID: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    # Load sensor data
    print("\nLoading sensor data from sensor_data.csv...")
    sensor_data = pd.read_csv('sensor_data.csv')
    print(f"Loaded {len(sensor_data)} data points (t=0 to {sensor_data['time'].max()}s)")

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Initialize state
    ego_speed = 0.0  # Start from rest
    results = []

    print("\nRunning simulation...")

    # Run simulation through all timesteps
    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC control command
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results for this timestep
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_error, 2) if dist_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        })

        # Update ego speed for next iteration (apply physics)
        ego_speed = max(0, ego_speed + accel_cmd * dt)

    # Create results dataframe
    results_df = pd.DataFrame(results)

    # Save to CSV
    print("\nSaving results to simulation_results.csv...")
    results_df.to_csv('simulation_results.csv', index=False)
    print(f"Saved {len(results_df)} rows")

    # Print summary statistics
    print("\n" + "=" * 60)
    print("Simulation Summary")
    print("=" * 60)

    # Cruise mode statistics
    cruise_data = results_df[results_df['mode'] == 'cruise']
    if len(cruise_data) > 0:
        print(f"\nCruise Mode ({len(cruise_data)} timesteps, {cruise_data['time'].iloc[0]:.1f}s - {cruise_data['time'].iloc[-1]:.1f}s):")
        print(f"  Final speed: {cruise_data['ego_speed'].iloc[-1]:.2f} m/s")
        print(f"  Target speed: {config['acc_settings']['set_speed']} m/s")
        print(f"  Max speed: {cruise_data['ego_speed'].max():.2f} m/s")

        # Find rise time (time to 90% of set speed)
        target_90 = 0.9 * config['acc_settings']['set_speed']
        rise_mask = cruise_data['ego_speed'] >= target_90
        if rise_mask.any():
            rise_time = cruise_data[rise_mask].iloc[0]['time']
            print(f"  Rise time (to 90%): {rise_time:.2f}s")

    # Follow mode statistics
    follow_data = results_df[results_df['mode'] == 'follow']
    if len(follow_data) > 0:
        # Filter out empty distance_error values
        follow_valid = follow_data[follow_data['distance_error'] != ''].copy()
        follow_valid['distance_error'] = pd.to_numeric(follow_valid['distance_error'])
        follow_valid['distance'] = pd.to_numeric(follow_valid['distance'])

        print(f"\nFollow Mode ({len(follow_data)} timesteps, {follow_data['time'].iloc[0]:.1f}s - {follow_data['time'].iloc[-1]:.1f}s):")
        if len(follow_valid) > 0:
            print(f"  Min distance: {follow_valid['distance'].min():.2f} m")
            print(f"  Mean distance error: {follow_valid['distance_error'].mean():.2f} m")
            print(f"  Max distance error: {follow_valid['distance_error'].abs().max():.2f} m")

            # Steady-state error (last 30% of follow phase)
            ss_start_idx = int(len(follow_valid) * 0.7)
            if ss_start_idx < len(follow_valid):
                ss_data = follow_valid.iloc[ss_start_idx:]
                ss_error = abs(ss_data['distance_error'].mean())
                print(f"  Steady-state distance error: {ss_error:.2f} m")

    # Emergency mode statistics
    emergency_data = results_df[results_df['mode'] == 'emergency']
    if len(emergency_data) > 0:
        print(f"\nEmergency Mode:")
        print(f"  Number of emergency events: {len(emergency_data)} timesteps")
        print(f"  Total emergency time: {len(emergency_data) * dt:.1f}s")

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)


if __name__ == '__main__':
    run_simulation()

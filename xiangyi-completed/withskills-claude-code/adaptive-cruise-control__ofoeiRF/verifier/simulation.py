"""Main simulation script for ACC system."""

import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """Run 150s ACC simulation and generate results."""
    print("="*80)
    print("Adaptive Cruise Control Simulation")
    print("="*80)

    # Load vehicle configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters from tuning_results.yaml
    print("\nLoading tuned PID parameters from tuning_results.yaml...")
    with open('tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Override config with tuned parameters
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    print(f"  Speed PID:    kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"  Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    # Load sensor data
    print("\nLoading sensor data from sensor_data.csv...")
    sensor_data = pd.read_csv('sensor_data.csv')
    print(f"  Duration: {sensor_data['time'].max()} seconds")
    print(f"  Timesteps: {len(sensor_data)}")

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    print(f"\nSimulation parameters:")
    print(f"  Set speed: {set_speed} m/s")
    print(f"  Time headway: {config['acc_settings']['time_headway']} s")
    print(f"  Min distance: {config['acc_settings']['min_distance']} m")
    print(f"  Emergency TTC threshold: {config['acc_settings']['emergency_ttc_threshold']} s")
    print(f"  Timestep: {dt} s")

    # Run simulation
    print("\nRunning simulation...")
    ego_speed = 0.0  # Initial speed ~0 m/s
    results = []

    for idx, row in sensor_data.iterrows():
        # Get sensor measurements
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC acceleration command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })

        # Update ego vehicle state
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot be negative

    # Convert to DataFrame
    df_results = pd.DataFrame(results)

    # Save results to CSV
    print(f"\nSaving results to simulation_results.csv...")
    df_results.to_csv('simulation_results.csv', index=False)
    print(f"  Saved {len(df_results)} rows")

    # Calculate and display performance metrics
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)

    # Speed metrics (cruise phase)
    cruise_data = df_results[df_results['mode'] == 'cruise']
    if len(cruise_data) > 0:
        target_90 = 0.9 * set_speed
        rise_data = cruise_data[cruise_data['ego_speed'] >= target_90]
        if len(rise_data) > 0:
            rise_time = rise_data.iloc[0]['time']
            print(f"\nSpeed Control (Cruise Mode):")
            print(f"  Rise time (0 to 90% of set speed):  {rise_time:.2f} s  (target: <10s)")

        max_speed_cruise = cruise_data['ego_speed'].max()
        overshoot_pct = max(0, (max_speed_cruise - set_speed) / set_speed * 100)
        print(f"  Overshoot:                           {overshoot_pct:.2f} %  (target: <5%)")

        # Steady-state error in last 5 seconds of cruise
        steady_cruise = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 5.0]
        if len(steady_cruise) > 0:
            speed_ss_error = abs(steady_cruise['ego_speed'].mean() - set_speed)
            print(f"  Steady-state error:                  {speed_ss_error:.4f} m/s  (target: <0.5 m/s)")

    # Distance metrics (follow phase)
    follow_data = df_results[(df_results['mode'] == 'follow') & (df_results['distance_error'] != '')]
    if len(follow_data) > 30:
        follow_data_copy = follow_data.copy()
        follow_data_copy['distance_error'] = pd.to_numeric(follow_data_copy['distance_error'])
        follow_data_copy['distance'] = pd.to_numeric(follow_data_copy['distance'])

        # Steady-state distance error (last 30% of follow mode)
        n_follow = len(follow_data_copy)
        steady_follow = follow_data_copy.iloc[int(0.7 * n_follow):]
        distance_ss_error = abs(steady_follow['distance_error'].mean())

        min_distance = follow_data_copy['distance'].min()

        print(f"\nDistance Control (Follow Mode):")
        print(f"  Distance steady-state error:         {distance_ss_error:.2f} m  (target: <2m)")
        print(f"  Minimum distance maintained:         {min_distance:.2f} m  (target: >5m)")

    # Mode distribution
    print(f"\nMode Distribution:")
    mode_counts = df_results['mode'].value_counts()
    for mode, count in mode_counts.items():
        percentage = (count / len(df_results)) * 100
        print(f"  {mode.capitalize():12s} {count:4d} steps ({percentage:5.1f}%)")

    # Emergency events
    emergency_count = len(df_results[df_results['mode'] == 'emergency'])
    if emergency_count > 0:
        print(f"\n⚠ WARNING: {emergency_count} emergency braking events detected")

    print(f"\nSimulation Duration: {df_results['time'].max()} seconds")
    print("="*80)
    print("✓ Simulation complete!")


if __name__ == '__main__':
    run_simulation()

"""ACC system simulation script."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """Run 150-second ACC simulation and generate results."""
    print("Loading configuration and tuned PID gains...")

    # Load base configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('tuning_results.yaml', 'r') as f:
        tuned_gains = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuned_gains['pid_speed']
    config['pid_distance'] = tuned_gains['pid_distance']

    print(f"Speed PID: Kp={config['pid_speed']['kp']}, Ki={config['pid_speed']['ki']}, Kd={config['pid_speed']['kd']}")
    print(f"Distance PID: Kp={config['pid_distance']['kp']}, Ki={config['pid_distance']['ki']}, Kd={config['pid_distance']['kd']}")

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')
    print(f"Loaded {len(sensor_data)} rows of sensor data")

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Initialize state
    ego_speed = 0.0

    # Results storage
    results = {
        'time': [],
        'ego_speed': [],
        'acceleration_cmd': [],
        'mode': [],
        'distance_error': [],
        'distance': [],
        'ttc': []
    }

    print("\nRunning simulation...")

    # Run simulation for all timesteps
    for idx, row in sensor_data.iterrows():
        t = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Clamp acceleration to vehicle limits
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))

        # Calculate TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Store results (empty string for None values per CSV format requirement)
        results['time'].append(t)
        results['ego_speed'].append(ego_speed)
        results['acceleration_cmd'].append(accel_cmd)
        results['mode'].append(mode)
        results['distance_error'].append(dist_error if dist_error is not None else '')
        results['distance'].append(distance if distance is not None else '')
        results['ttc'].append(ttc if ttc is not None else '')

        # Update ego vehicle state
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Prevent negative speed

        # Progress indicator
        if (idx + 1) % 300 == 0:
            print(f"  Progress: {t:.1f}s / 150.0s")

    print("Simulation complete!")

    # Convert to DataFrame
    df_results = pd.DataFrame(results)

    # Save to CSV
    df_results.to_csv('simulation_results.csv', index=False)
    print(f"\nResults saved to simulation_results.csv ({len(df_results)} rows)")

    # Calculate and print performance metrics
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)

    # Speed control metrics (first 30 seconds - cruise mode)
    cruise_mask = df_results['time'] <= 30.0
    cruise_data = df_results[cruise_mask]
    set_speed = config['acc_settings']['set_speed']

    # Rise time (10% to 90% of set speed)
    idx_10 = cruise_data[cruise_data['ego_speed'] >= 0.1 * set_speed].index
    idx_90 = cruise_data[cruise_data['ego_speed'] >= 0.9 * set_speed].index

    if len(idx_10) > 0 and len(idx_90) > 0:
        t_10 = cruise_data.loc[idx_10[0], 'time']
        t_90 = cruise_data.loc[idx_90[0], 'time']
        rise_time = t_90 - t_10
    else:
        rise_time = None

    # Overshoot
    max_speed = cruise_data['ego_speed'].max()
    overshoot = max(0, ((max_speed - set_speed) / set_speed) * 100)

    # Steady-state error (last 5 seconds of cruise)
    steady_state_data = cruise_data.tail(50)  # Last 5s at 0.1s timestep
    steady_state_error = abs(steady_state_data['ego_speed'].mean() - set_speed)

    print("\nSpeed Control (Cruise Mode):")
    if rise_time is not None:
        print(f"  Rise Time (10%-90%): {rise_time:.2f}s (target: <10s) {'✓' if rise_time <= 10 else '✗'}")
    print(f"  Overshoot: {overshoot:.2f}% (target: <5%) {'✓' if overshoot <= 5 else '✗'}")
    print(f"  Steady-State Error: {steady_state_error:.3f} m/s (target: <0.5 m/s) {'✓' if steady_state_error <= 0.5 else '✗'}")

    # Distance control metrics (when following)
    follow_data = df_results[df_results['mode'] == 'follow']

    if len(follow_data) > 0:
        # Filter out empty distance_error values and convert to float
        distance_errors = follow_data['distance_error']
        distance_errors = distance_errors[distance_errors != ''].astype(float)

        if len(distance_errors) > 0:
            # Steady-state distance error (last 20 seconds of following)
            final_errors = distance_errors.tail(200) if len(distance_errors) >= 200 else distance_errors
            distance_steady_state_error = final_errors.abs().mean()

            print("\nDistance Control (Follow Mode):")
            print(f"  Steady-State Error: {distance_steady_state_error:.3f} m (target: <2m) {'✓' if distance_steady_state_error <= 2 else '✗'}")

    # Minimum distance
    distances = df_results['distance']
    distances = distances[distances != ''].astype(float)

    if len(distances) > 0:
        min_distance = distances.min()
        print(f"  Minimum Distance: {min_distance:.2f} m (target: >5m) {'✓' if min_distance > 5 else '✗'}")

    # TTC statistics
    ttc_values = df_results['ttc']
    ttc_values = ttc_values[ttc_values != ''].astype(float)

    if len(ttc_values) > 0:
        min_ttc = ttc_values.min()
        mean_ttc = ttc_values.mean()
        print(f"\nTime-to-Collision Statistics:")
        print(f"  Minimum TTC: {min_ttc:.2f}s")
        print(f"  Mean TTC: {mean_ttc:.2f}s")

    # Mode distribution
    print(f"\nMode Distribution:")
    for mode in ['cruise', 'follow', 'emergency']:
        count = len(df_results[df_results['mode'] == mode])
        percentage = (count / len(df_results)) * 100
        print(f"  {mode.capitalize()}: {count} steps ({percentage:.1f}%)")

    print("\n" + "="*80)

    return df_results


if __name__ == '__main__':
    run_simulation()

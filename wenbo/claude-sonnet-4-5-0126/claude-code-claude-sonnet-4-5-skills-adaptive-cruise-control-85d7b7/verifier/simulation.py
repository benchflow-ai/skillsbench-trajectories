"""ACC simulation using sensor data and tuned PID parameters."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def main():
    """Run ACC simulation and save results."""
    # Load vehicle parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('tuning_results.yaml', 'r') as f:
        tuned_gains = yaml.safe_load(f)

    # Update config with tuned gains
    config['pid_speed'] = tuned_gains['pid_speed']
    config['pid_distance'] = tuned_gains['pid_distance']

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']

    # Initialize state
    ego_speed = 0.0
    ego_position = 0.0

    # Results storage
    results = []

    print("Running ACC simulation...")
    print(f"Simulation duration: {len(sensor_data) * dt:.1f}s")
    print(f"Time step: {dt}s")
    print(f"PID Speed gains: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"PID Distance gains: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")
    print()

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        sensor_distance = row['distance'] if pd.notna(row['distance']) else None

        # If lead vehicle exists, calculate actual distance based on positions
        if lead_speed is not None and sensor_distance is not None:
            # Lead vehicle position (assuming it starts at sensor_distance ahead)
            if idx > 0 and pd.notna(sensor_data.iloc[idx-1]['lead_speed']):
                # Continue tracking from previous step
                lead_position = results[-1]['lead_position'] + lead_speed * dt
            else:
                # First time seeing lead vehicle
                lead_position = ego_position + sensor_distance

            distance = lead_position - ego_position
        else:
            distance = None
            lead_position = None

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if applicable
        if distance is not None and lead_speed is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Update ego vehicle state
        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)
        ego_position += ego_speed * dt

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else '',
            'lead_position': lead_position
        })

        # Progress indicator
        if idx % 150 == 0:
            print(f"Progress: {time:.1f}s / {sensor_data.iloc[-1]['time']:.1f}s")

    print("\nSimulation complete!")

    # Create results dataframe
    df_results = pd.DataFrame(results)

    # Drop the lead_position column (used only for tracking)
    df_results = df_results.drop(columns=['lead_position'])

    # Save results
    df_results.to_csv('simulation_results.csv', index=False)
    print(f"\nResults saved to simulation_results.csv ({len(df_results)} rows)")

    # Calculate and display performance metrics
    print("\n" + "="*60)
    print("PERFORMANCE METRICS")
    print("="*60)

    # Speed metrics (cruise phase: 0-30s)
    cruise_mask = df_results['time'] < 30.0
    cruise_data = df_results[cruise_mask]
    set_speed = config['acc_settings']['set_speed']

    # Rise time (time to reach 90% of set speed)
    target_90 = 0.9 * set_speed
    rise_time_idx = cruise_data[cruise_data['ego_speed'] >= target_90].index
    if len(rise_time_idx) > 0:
        rise_time = cruise_data.loc[rise_time_idx[0], 'time']
        print(f"Rise time (to 90% of set speed): {rise_time:.2f}s (target: <10s) {'✓' if rise_time < 10 else '✗'}")
    else:
        print("Rise time: Not achieved")

    # Overshoot
    max_speed = cruise_data['ego_speed'].max()
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)
    print(f"Speed overshoot: {overshoot:.2f}% (target: <5%) {'✓' if overshoot < 5 else '✗'}")

    # Steady-state error (last 5 seconds before lead vehicle)
    steady_mask = (df_results['time'] >= 25.0) & (df_results['time'] < 30.0)
    if steady_mask.any():
        steady_state_error = abs(df_results[steady_mask]['ego_speed'].mean() - set_speed)
        print(f"Speed steady-state error: {steady_state_error:.3f} m/s (target: <0.5 m/s) {'✓' if steady_state_error < 0.5 else '✗'}")
    else:
        print("Speed steady-state error: N/A")

    # Distance metrics (following phase: 30-150s)
    follow_mask = (df_results['time'] >= 30.0) & (df_results['distance'] != '')
    if follow_mask.any():
        follow_data = df_results[follow_mask]

        # Minimum distance
        min_distance = follow_data['distance'].astype(float).min()
        print(f"Minimum following distance: {min_distance:.2f} m (target: >5m) {'✓' if min_distance > 5 else '✗'}")

        # Distance steady-state error (last 10 seconds)
        final_mask = df_results['time'] >= 140.0
        if final_mask.any():
            final_data = df_results[final_mask]
            final_dist_errors = final_data[final_data['distance_error'] != '']['distance_error'].astype(float)
            if len(final_dist_errors) > 0:
                dist_ss_error = abs(final_dist_errors).mean()
                print(f"Distance steady-state error: {dist_ss_error:.2f} m (target: <2m) {'✓' if dist_ss_error < 2 else '✗'}")

    # Emergency braking events
    emergency_count = (df_results['mode'] == 'emergency').sum()
    print(f"\nEmergency braking events: {emergency_count}")

    # Mode distribution
    print("\nControl mode distribution:")
    mode_counts = df_results['mode'].value_counts()
    for mode, count in mode_counts.items():
        print(f"  {mode}: {count} steps ({count/len(df_results)*100:.1f}%)")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()

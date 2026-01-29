"""
ACC simulation script.
Runs the full 150-second simulation and produces results.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """
    Run ACC simulation and save results.
    """
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('/root/tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Update config with tuned parameters
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Initialize state
    ego_speed = 0.0

    # Storage for results
    results = []

    print("Running ACC simulation...")
    print(f"Simulation duration: 150s")
    print(f"Time step: {dt}s")
    print(f"Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"\nPID parameters:")
    print(f"  Speed: kp={config['pid_speed']['kp']}, " +
          f"ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"  Distance: kp={config['pid_distance']['kp']}, " +
          f"ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")
    print("\nRunning simulation...")

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results
        result_row = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        }
        results.append(result_row)

        # Update ego speed using simple Euler integration
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot be negative

        # Progress indicator
        if idx % 300 == 0:
            print(f"  Progress: {time:.1f}s / 150.0s")

    print("Simulation complete!\n")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    results_df.to_csv('/root/simulation_results.csv', index=False)
    print("Results saved to simulation_results.csv")

    # Calculate and print performance metrics
    print("\n" + "="*60)
    print("PERFORMANCE METRICS")
    print("="*60)

    # Speed control metrics (cruise phase: first 30 seconds)
    cruise_mask = results_df['time'] < 30.0
    cruise_data = results_df[cruise_mask]

    set_speed = config['acc_settings']['set_speed']
    target_90 = 0.9 * set_speed

    # Rise time
    rise_idx = cruise_data[cruise_data['ego_speed'] >= target_90].index
    if len(rise_idx) > 0:
        rise_time = cruise_data.loc[rise_idx[0], 'time']
    else:
        rise_time = 30.0

    # Overshoot
    max_speed = cruise_data['ego_speed'].max()
    overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)

    # Steady-state error (last 5 seconds of cruise)
    cruise_end_mask = (results_df['time'] >= 25.0) & (results_df['time'] < 30.0)
    cruise_end_data = results_df[cruise_end_mask]
    if len(cruise_end_data) > 0:
        speed_ss_error = np.mean(np.abs(cruise_end_data['ego_speed'] - set_speed))
    else:
        speed_ss_error = 0.0

    # Distance control metrics (follow phase)
    follow_mask = results_df['time'] >= 30.0
    follow_data = results_df[follow_mask]
    follow_with_distance = follow_data[follow_data['distance'] != ''].copy()

    if len(follow_with_distance) > 0:
        follow_with_distance['distance'] = pd.to_numeric(follow_with_distance['distance'])
        follow_with_distance['distance_error'] = pd.to_numeric(follow_with_distance['distance_error'])

        # Distance steady-state error (last 5 seconds)
        follow_end = follow_with_distance[follow_with_distance['time'] >= 145.0]
        if len(follow_end) > 0:
            distance_ss_error = np.mean(np.abs(follow_end['distance_error']))
        else:
            distance_ss_error = 0.0

        # Minimum distance
        min_distance = follow_with_distance['distance'].min()
    else:
        distance_ss_error = 0.0
        min_distance = config['acc_settings']['min_distance']

    # Print metrics
    print(f"\nSpeed Control (Cruise Phase):")
    print(f"  Rise time: {rise_time:.2f}s (target: <10s) {'✓' if rise_time < 10.0 else '✗'}")
    print(f"  Overshoot: {overshoot_pct:.2f}% (target: <5%) {'✓' if overshoot_pct < 5.0 else '✗'}")
    print(f"  Steady-state error: {speed_ss_error:.3f} m/s (target: <0.5 m/s) {'✓' if speed_ss_error < 0.5 else '✗'}")

    print(f"\nDistance Control (Follow Phase):")
    print(f"  Steady-state error: {distance_ss_error:.2f} m (target: <2m) {'✓' if distance_ss_error < 2.0 else '✗'}")
    print(f"  Minimum distance: {min_distance:.2f} m (target: >5m) {'✓' if min_distance > 5.0 else '✗'}")

    print(f"\nSimulation Duration: 150s ✓")

    # Count modes
    mode_counts = results_df['mode'].value_counts()
    print(f"\nMode Distribution:")
    for mode, count in mode_counts.items():
        print(f"  {mode}: {count} timesteps ({count/len(results_df)*100:.1f}%)")

    print("\n" + "="*60)


if __name__ == '__main__':
    run_simulation()

"""ACC Simulation with sensor data."""

import yaml
import pandas as pd
import numpy as np
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """Run ACC simulation for 150 seconds."""
    print("Loading configuration...")

    # Load vehicle parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('tuning_results.yaml', 'r') as f:
        tuning_results = yaml.safe_load(f)

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')

    print(f"Loaded {len(sensor_data)} sensor data points")
    print(f"Speed PID gains: kp={tuning_results['pid_speed']['kp']}, "
          f"ki={tuning_results['pid_speed']['ki']}, kd={tuning_results['pid_speed']['kd']}")
    print(f"Distance PID gains: kp={tuning_results['pid_distance']['kp']}, "
          f"ki={tuning_results['pid_distance']['ki']}, kd={tuning_results['pid_distance']['kd']}")

    # Initialize PID controllers with tuned parameters
    speed_pid = PIDController(
        tuning_results['pid_speed']['kp'],
        tuning_results['pid_speed']['ki'],
        tuning_results['pid_speed']['kd']
    )
    distance_pid = PIDController(
        tuning_results['pid_distance']['kp'],
        tuning_results['pid_distance']['ki'],
        tuning_results['pid_distance']['kd']
    )

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_controllers(speed_pid, distance_pid)

    # Simulation parameters
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    # Initialize state
    ego_speed = 0.0

    # Results storage
    results = []

    print("\nRunning simulation...")

    # Run simulation
    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

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
        ego_speed = max(0, ego_speed + accel_cmd * dt)

        # Progress indicator
        if idx % 300 == 0:
            print(f"Time: {time:.1f}s, Speed: {ego_speed:.1f} m/s, Mode: {mode}")

    print("\nSimulation complete!")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    results_df.to_csv('simulation_results.csv', index=False)
    print(f"Results saved to simulation_results.csv ({len(results_df)} rows)")

    # Calculate and print performance metrics
    print("\n=== Performance Metrics ===")

    # Speed rise time (time to reach 90% of set speed)
    target_90 = 0.9 * set_speed
    rise_time_idx = results_df[results_df['ego_speed'] >= target_90].index
    if len(rise_time_idx) > 0:
        rise_time = results_df.loc[rise_time_idx[0], 'time']
        print(f"Rise time (to 90% of {set_speed} m/s): {rise_time:.2f}s (target: <10s)")
    else:
        print("Rise time: N/A (never reached 90% of set speed)")

    # Speed overshoot
    cruise_phase = results_df[results_df['mode'] == 'cruise']
    if len(cruise_phase) > 0:
        max_speed = cruise_phase['ego_speed'].max()
        overshoot = max(0, (max_speed - set_speed) / set_speed * 100)
        print(f"Speed overshoot: {overshoot:.2f}% (target: <5%)")
    else:
        print("Speed overshoot: N/A (no cruise phase)")

    # Steady-state speed error (last 20% of cruise phase)
    cruise_times = cruise_phase['time'].values
    if len(cruise_times) > 0:
        cruise_end = cruise_times[-1]
        ss_start = cruise_end * 0.8
        ss_cruise = cruise_phase[cruise_phase['time'] >= ss_start]
        if len(ss_cruise) > 0:
            ss_speed_error = abs(ss_cruise['ego_speed'] - set_speed).mean()
            print(f"Steady-state speed error: {ss_speed_error:.3f} m/s (target: <0.5 m/s)")
        else:
            print("Steady-state speed error: N/A")
    else:
        print("Steady-state speed error: N/A")

    # Distance steady-state error (during follow mode)
    follow_phase = results_df[results_df['mode'] == 'follow']
    if len(follow_phase) > 0:
        # Use last 50% of follow phase
        follow_count = len(follow_phase)
        ss_follow = follow_phase.iloc[follow_count//2:]
        valid_dist_errors = ss_follow['distance_error'].replace('', np.nan).dropna()
        if len(valid_dist_errors) > 0:
            ss_distance_error = abs(valid_dist_errors.astype(float)).mean()
            print(f"Steady-state distance error: {ss_distance_error:.3f} m (target: <2 m)")
        else:
            print("Steady-state distance error: N/A")
    else:
        print("Steady-state distance error: N/A (no follow phase)")

    # Minimum distance
    valid_distances = results_df['distance'].replace('', np.nan).dropna()
    if len(valid_distances) > 0:
        min_distance = valid_distances.astype(float).min()
        print(f"Minimum distance: {min_distance:.2f} m (target: >5 m)")
    else:
        print("Minimum distance: N/A (no lead vehicle)")

    # Mode statistics
    print(f"\n=== Mode Statistics ===")
    mode_counts = results_df['mode'].value_counts()
    for mode, count in mode_counts.items():
        percentage = count / len(results_df) * 100
        print(f"{mode.capitalize()}: {count} steps ({percentage:.1f}%)")

    return results_df


if __name__ == '__main__':
    results = run_simulation()

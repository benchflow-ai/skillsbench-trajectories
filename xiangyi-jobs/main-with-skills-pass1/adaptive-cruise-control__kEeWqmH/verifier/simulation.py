import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def main():
    # Load configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('/root/tuning_results.yaml', 'r') as f:
        tuning_results = yaml.safe_load(f)

    # Override config with tuned parameters
    config['pid_speed'] = tuning_results['pid_speed']
    config['pid_distance'] = tuning_results['pid_distance']

    # Load sensor data
    sensor_df = pd.read_csv('/root/sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    ego_speed = 0.0

    # Results storage
    results = []

    print("Running ACC simulation...")

    for idx, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if applicable
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        # Store results
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

        # Update ego speed for next iteration
        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)

        # Progress indicator
        if idx % 300 == 0:
            print(f"  Time: {time:.1f}s / 150.0s")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Save to CSV
    results_df.to_csv('/root/simulation_results.csv', index=False)

    print("\nSimulation complete!")
    print(f"Results saved to simulation_results.csv ({len(results_df)} rows)")

    # Calculate and display performance metrics
    print("\n=== Performance Metrics ===")

    # Speed rise time (time to reach 90% of set speed)
    set_speed = config['acc_settings']['set_speed']
    target_speed = 0.9 * set_speed
    rise_time = None
    for idx, row in results_df.iterrows():
        if row['ego_speed'] >= target_speed:
            rise_time = row['time']
            break
    print(f"Speed rise time: {rise_time:.2f}s (target: <10s)")

    # Speed overshoot (check first 30 seconds)
    cruise_phase = results_df[results_df['time'] <= 30.0]
    max_speed = cruise_phase['ego_speed'].max()
    overshoot = max(0, (max_speed - set_speed) / set_speed * 100)
    print(f"Speed overshoot: {overshoot:.2f}% (target: <5%)")

    # Speed steady-state error (20-30s cruise phase)
    cruise_steady = results_df[(results_df['time'] >= 20.0) & (results_df['time'] <= 30.0)]
    speed_sse = abs(cruise_steady['ego_speed'].mean() - set_speed)
    print(f"Speed steady-state error: {speed_sse:.3f} m/s (target: <0.5 m/s)")

    # Distance steady-state error (last 50s of following)
    follow_phase = results_df[(results_df['mode'] == 'follow') & (results_df['time'] >= 100.0)]
    if not follow_phase.empty:
        distance_errors = follow_phase['distance_error'].replace('', np.nan).dropna().astype(float)
        if not distance_errors.empty:
            distance_sse = abs(distance_errors).mean()
            print(f"Distance steady-state error: {distance_sse:.3f} m (target: <2 m)")
        else:
            print("Distance steady-state error: N/A (no follow phase data)")
    else:
        print("Distance steady-state error: N/A (no follow phase)")

    # Minimum distance safety check
    distances = results_df['distance'].replace('', np.nan).dropna().astype(float)
    if not distances.empty:
        min_distance = distances.min()
        print(f"Minimum distance: {min_distance:.2f} m (target: >5 m)")
    else:
        print("Minimum distance: N/A (no lead vehicle)")

    # Control duration
    control_duration = results_df['time'].max()
    print(f"Control duration: {control_duration:.1f}s (target: 150s)")

    print("\n=== Mode Distribution ===")
    mode_counts = results_df['mode'].value_counts()
    for mode, count in mode_counts.items():
        percentage = (count / len(results_df)) * 100
        print(f"{mode}: {count} steps ({percentage:.1f}%)")


if __name__ == "__main__":
    main()

"""ACC System Simulation - Improved version with proper relative motion."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """Run the full ACC simulation for 150 seconds."""
    print("=" * 70)
    print("Adaptive Cruise Control Simulation")
    print("=" * 70)

    # Load vehicle parameters and ACC settings
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('tuning_results.yaml', 'r') as f:
        tuned_gains = yaml.safe_load(f)

    # Override config with tuned gains
    config['pid_speed'] = tuned_gains['pid_speed']
    config['pid_distance'] = tuned_gains['pid_distance']

    print("\nConfiguration:")
    print(f"  Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"  Time headway: {config['acc_settings']['time_headway']} s")
    print(f"  Min distance: {config['acc_settings']['min_distance']} m")
    print(f"  Emergency TTC threshold: {config['acc_settings']['emergency_ttc_threshold']} s")
    print(f"\nSpeed PID: Kp={config['pid_speed']['kp']}, Ki={config['pid_speed']['ki']}, Kd={config['pid_speed']['kd']}")
    print(f"Distance PID: Kp={config['pid_distance']['kp']}, Ki={config['pid_distance']['ki']}, Kd={config['pid_distance']['kd']}")

    # Load sensor data (lead vehicle information)
    sensor_df = pd.read_csv('sensor_data.csv')

    # Simulation parameters
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize ego vehicle state
    ego_speed = 0.0  # Start from rest
    ego_position = 0.0  # Track position for relative distance calculation

    # Initialize lead vehicle state
    lead_position = 0.0
    prev_lead_speed = None
    prev_distance_sensor = None

    # Storage for results
    results = []

    # Simulation loop
    print(f"\nRunning simulation for {len(sensor_df)} time steps ({len(sensor_df) * dt:.1f}s)...")

    for idx, row in sensor_df.iterrows():
        time = row['time']

        # Get lead vehicle information from sensor data
        lead_speed_sensor = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance_sensor = row['distance'] if pd.notna(row['distance']) else None

        # Initialize or update lead vehicle position
        if lead_speed_sensor is not None and distance_sensor is not None:
            if prev_distance_sensor is None:
                # First detection of lead vehicle
                lead_position = ego_position + distance_sensor
                prev_lead_speed = lead_speed_sensor
                prev_distance_sensor = distance_sensor
            else:
                # Update lead position based on its speed
                lead_position += prev_lead_speed * dt
                prev_lead_speed = lead_speed_sensor

            # Calculate actual distance based on positions
            distance = lead_position - ego_position
        else:
            distance = None
            lead_speed_sensor = None

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed_sensor, distance, dt)

        # Calculate TTC if applicable
        if lead_speed_sensor is not None and distance is not None:
            relative_speed = ego_speed - lead_speed_sensor
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results for this time step
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': f'{ttc:.2f}' if ttc is not None else ''
        })

        # Update ego vehicle state (Euler integration)
        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)
        ego_position += ego_speed * dt

        # Progress indicator
        if idx % 300 == 0:
            print(f"  t={time:.1f}s: speed={ego_speed:.2f}m/s, mode={mode}")

    print(f"\nSimulation complete!")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Save to CSV
    results_df.to_csv('simulation_results.csv', index=False)
    print(f"\nResults saved to simulation_results.csv ({len(results_df)} rows)")

    # Calculate and display performance metrics
    print("\n" + "=" * 70)
    print("Performance Metrics")
    print("=" * 70)

    # 1. Speed rise time (time to reach 90% of set speed)
    rise_threshold = 0.9 * set_speed
    rise_time_idx = results_df[results_df['ego_speed'] >= rise_threshold].index
    if len(rise_time_idx) > 0:
        rise_time = results_df.iloc[rise_time_idx[0]]['time']
        print(f"\n1. Speed Rise Time: {rise_time:.2f}s (target: <10s) {'✓' if rise_time < 10 else '✗'}")
    else:
        print(f"\n1. Speed Rise Time: NOT REACHED")

    # 2. Speed overshoot (during cruise phase, first 30s)
    cruise_phase = results_df[results_df['time'] <= 30.0]
    max_speed_cruise = cruise_phase['ego_speed'].max()
    overshoot_percent = max(0, (max_speed_cruise - set_speed) / set_speed * 100)
    print(f"2. Speed Overshoot: {overshoot_percent:.2f}% (target: <5%) {'✓' if overshoot_percent < 5 else '✗'}")

    # 3. Speed steady-state error (last 5s of cruise mode, t=25-30s)
    cruise_steady = results_df[(results_df['time'] >= 25.0) & (results_df['time'] <= 30.0)]
    if len(cruise_steady) > 0:
        speed_ss_error = abs(cruise_steady['ego_speed'].mean() - set_speed)
        print(f"3. Speed Steady-State Error: {speed_ss_error:.3f} m/s (target: <0.5 m/s) {'✓' if speed_ss_error < 0.5 else '✗'}")
    else:
        print(f"3. Speed Steady-State Error: N/A")

    # 4. Distance steady-state error (following mode, last 30% of following period)
    follow_data = results_df[results_df['mode'] == 'follow']
    if len(follow_data) > 0:
        steady_idx = int(len(follow_data) * 0.7)
        steady_follow = follow_data.iloc[steady_idx:]
        distance_errors = steady_follow['distance_error'].apply(
            lambda x: abs(float(x)) if x != '' else None
        ).dropna()
        if len(distance_errors) > 0:
            dist_ss_error = distance_errors.mean()
            print(f"4. Distance Steady-State Error: {dist_ss_error:.3f} m (target: <2m) {'✓' if dist_ss_error < 2 else '✗'}")
        else:
            print(f"4. Distance Steady-State Error: N/A (no valid data)")
    else:
        print(f"4. Distance Steady-State Error: N/A (no following mode)")

    # 5. Minimum distance (safety critical)
    distances = results_df['distance'].apply(
        lambda x: float(x) if x != '' else None
    ).dropna()
    if len(distances) > 0:
        min_distance = distances.min()
        print(f"5. Minimum Distance: {min_distance:.2f} m (target: >5m) {'✓' if min_distance > 5 else '✗'}")
    else:
        print(f"5. Minimum Distance: N/A (no lead vehicle)")

    # Mode statistics
    mode_counts = results_df['mode'].value_counts()
    print(f"\nMode Distribution:")
    for mode, count in mode_counts.items():
        duration = count * dt
        print(f"  {mode}: {duration:.1f}s ({count/len(results_df)*100:.1f}%)")

    print("\n" + "=" * 70)

    return results_df


if __name__ == '__main__':
    run_simulation()

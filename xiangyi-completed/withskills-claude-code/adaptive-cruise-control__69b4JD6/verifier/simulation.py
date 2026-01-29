"""ACC System Simulation."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load configuration from vehicle_params.yaml and tuning_results.yaml."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters from tuning_results.yaml
    with open('tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Override with tuned parameters
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    return config


def load_sensor_data():
    """Load sensor data from CSV."""
    return pd.read_csv('sensor_data.csv')


def calculate_ttc(ego_speed, lead_speed, distance):
    """
    Calculate Time-To-Collision (TTC).

    Args:
        ego_speed: Ego vehicle speed (m/s)
        lead_speed: Lead vehicle speed (m/s) or None
        distance: Distance to lead vehicle (m) or None

    Returns:
        float: TTC in seconds, or None if not applicable
    """
    if lead_speed is None or distance is None:
        return None

    relative_speed = ego_speed - lead_speed

    if relative_speed > 0 and distance > 0:
        return distance / relative_speed
    else:
        return None


def run_simulation():
    """Run the ACC simulation."""
    print("Loading configuration and sensor data...")
    config = load_config()
    sensor_data = load_sensor_data()

    print(f"Loaded PID parameters:")
    print(f"  Speed PID: kp={config['pid_speed']['kp']}, "
          f"ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"  Distance PID: kp={config['pid_distance']['kp']}, "
          f"ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize state
    ego_speed = 0.0
    dt = config['simulation']['dt']

    # Storage for results
    results = []

    print("\nRunning simulation...")

    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error if dist_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })

        # Update ego speed for next iteration
        if idx < len(sensor_data) - 1:
            ego_speed += accel_cmd * dt
            ego_speed = max(0, ego_speed)  # Speed cannot be negative

        if idx % 300 == 0:
            print(f"  Time: {time:.1f}s, Speed: {ego_speed:.2f} m/s, Mode: {mode}")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Save to CSV
    results_df.to_csv('simulation_results.csv', index=False)

    print(f"\nSimulation complete!")
    print(f"Results saved to simulation_results.csv ({len(results_df)} rows)")

    # Print summary statistics
    print("\n" + "="*60)
    print("SIMULATION SUMMARY")
    print("="*60)

    # Speed statistics (during cruise mode)
    cruise_mask = results_df['mode'] == 'cruise'
    if cruise_mask.any():
        cruise_speeds = results_df.loc[cruise_mask, 'ego_speed']
        print(f"\nCruise Mode Statistics:")
        print(f"  Duration: {cruise_mask.sum() * dt:.1f}s")
        print(f"  Max speed: {cruise_speeds.max():.2f} m/s")
        print(f"  Avg speed: {cruise_speeds.mean():.2f} m/s")
        print(f"  Final speed: {cruise_speeds.iloc[-1]:.2f} m/s")

        # Calculate rise time
        set_speed = config['acc_settings']['set_speed']
        speed_10 = 0.1 * set_speed
        speed_90 = 0.9 * set_speed

        idx_10 = results_df[results_df['ego_speed'] >= speed_10].index
        idx_90 = results_df[results_df['ego_speed'] >= speed_90].index

        if len(idx_10) > 0 and len(idx_90) > 0:
            rise_time = results_df.loc[idx_90[0], 'time'] - results_df.loc[idx_10[0], 'time']
            print(f"  Rise time (10%-90%): {rise_time:.2f}s")

        # Overshoot
        overshoot = max(0, (cruise_speeds.max() - set_speed) / set_speed * 100)
        print(f"  Overshoot: {overshoot:.2f}%")

        # Steady-state error (last 20% of cruise)
        cruise_indices = results_df[cruise_mask].index
        steady_start = int(cruise_indices[0] + 0.8 * len(cruise_indices))
        if steady_start < cruise_indices[-1]:
            steady_speeds = results_df.loc[cruise_indices[steady_start]:, 'ego_speed']
            sse = (steady_speeds - set_speed).abs().mean()
            print(f"  Steady-state error: {sse:.3f} m/s")

    # Follow mode statistics
    follow_mask = results_df['mode'] == 'follow'
    if follow_mask.any():
        print(f"\nFollow Mode Statistics:")
        print(f"  Duration: {follow_mask.sum() * dt:.1f}s")

        follow_dist_errors = pd.to_numeric(
            results_df.loc[follow_mask, 'distance_error'], errors='coerce'
        )
        follow_distances = pd.to_numeric(
            results_df.loc[follow_mask, 'distance'], errors='coerce'
        )

        print(f"  Min distance: {follow_distances.min():.2f} m")
        print(f"  Avg distance: {follow_distances.mean():.2f} m")

        # Steady-state distance error (last 80% of follow)
        follow_indices = results_df[follow_mask].index
        steady_start = int(follow_indices[0] + 0.2 * len(follow_indices))
        if steady_start < follow_indices[-1]:
            steady_dist_errors = follow_dist_errors.loc[follow_indices[steady_start]:]
            dist_sse = steady_dist_errors.abs().mean()
            print(f"  Steady-state distance error: {dist_sse:.2f} m")

    # Emergency mode statistics
    emergency_mask = results_df['mode'] == 'emergency'
    if emergency_mask.any():
        print(f"\nEmergency Mode Statistics:")
        print(f"  Activations: {emergency_mask.sum()} timesteps")
        print(f"  Duration: {emergency_mask.sum() * dt:.1f}s")

    # Mode distribution
    print(f"\nMode Distribution:")
    for mode in ['cruise', 'follow', 'emergency']:
        count = (results_df['mode'] == mode).sum()
        pct = count / len(results_df) * 100
        print(f"  {mode.capitalize()}: {count} timesteps ({pct:.1f}%)")

    return results_df


if __name__ == '__main__':
    run_simulation()

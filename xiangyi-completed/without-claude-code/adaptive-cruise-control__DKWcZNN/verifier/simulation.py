"""ACC simulation using tuned PID parameters."""

import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def run_acc_simulation():
    """Run 150s ACC simulation and save results."""
    print("Running ACC Simulation")
    print("=" * 70)

    # Load vehicle parameters
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains
    with open('/root/tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Override config with tuned parameters
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    print("\nLoaded PID Parameters:")
    print(f"  Speed PID:    kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"  Distance PID: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')
    print(f"\nSensor data: {len(sensor_data)} timesteps (t=0 to t={sensor_data['time'].max()}s)")

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    # Initialize state
    ego_speed = 0.0

    # Storage for results
    results = []

    print("\nRunning simulation...")

    # Run simulation for each timestep
    for idx, row in sensor_data.iterrows():
        # Get sensor readings
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego vehicle speed (simple integration)
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # No negative speeds

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Progress indicator
        if idx % 300 == 0:
            print(f"  t = {time:6.1f}s, mode = {mode:9s}, ego_speed = {ego_speed:5.2f} m/s")

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Save to CSV
    results_df.to_csv('/root/simulation_results.csv', index=False)

    print(f"\n✓ Simulation complete")
    print(f"✓ Results saved to simulation_results.csv ({len(results_df)} rows)")

    # Print summary statistics
    print("\n" + "=" * 70)
    print("Simulation Summary")
    print("=" * 70)

    cruise_data = results_df[results_df['mode'] == 'cruise']
    follow_data = results_df[results_df['mode'] == 'follow']
    emergency_data = results_df[results_df['mode'] == 'emergency']

    print(f"\nMode distribution:")
    print(f"  Cruise:    {len(cruise_data):4d} timesteps ({len(cruise_data)/len(results_df)*100:5.1f}%)")
    print(f"  Follow:    {len(follow_data):4d} timesteps ({len(follow_data)/len(results_df)*100:5.1f}%)")
    print(f"  Emergency: {len(emergency_data):4d} timesteps ({len(emergency_data)/len(results_df)*100:5.1f}%)")

    if len(cruise_data) > 0:
        print(f"\nCruise mode performance:")
        print(f"  Max speed:  {cruise_data['ego_speed'].max():.2f} m/s")
        print(f"  Final speed: {cruise_data['ego_speed'].iloc[-1]:.2f} m/s (target: {set_speed} m/s)")

        # Rise time
        above_90 = cruise_data[cruise_data['ego_speed'] >= 0.9 * set_speed]
        if len(above_90) > 0:
            rise_time = above_90['time'].iloc[0]
            print(f"  Rise time to 90%: {rise_time:.2f}s")

        # Overshoot
        overshoot = (cruise_data['ego_speed'].max() - set_speed) / set_speed * 100
        print(f"  Overshoot: {overshoot:.2f}%")

    if len(follow_data) > 0:
        print(f"\nFollow mode performance:")
        valid_dist_err = follow_data['distance_error'].dropna()
        if len(valid_dist_err) > 0:
            print(f"  Avg distance error: {valid_dist_err.mean():.2f} m")
            print(f"  Distance error std: {valid_dist_err.std():.2f} m")

    # Safety metrics
    all_distances = results_df['distance'].dropna()
    if len(all_distances) > 0:
        print(f"\nSafety metrics:")
        print(f"  Minimum distance: {all_distances.min():.2f} m")
        print(f"  Average distance: {all_distances.mean():.2f} m")

    print("\n" + "=" * 70)
    print("Simulation complete!")
    print("=" * 70)


if __name__ == '__main__':
    run_acc_simulation()

"""ACC System Simulation

Runs a 150-second simulation of the Adaptive Cruise Control system using
sensor data and PID gains from configuration files.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def calculate_ttc(ego_speed, lead_speed, distance):
    """Calculate time-to-collision.

    Args:
        ego_speed: Ego vehicle speed (m/s)
        lead_speed: Lead vehicle speed (m/s)
        distance: Distance to lead vehicle (m)

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
    """Run the ACC simulation for 150 seconds."""
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
    dt = config['simulation']['dt']

    # Simulation state
    ego_speed = 0.0  # Initial speed ~0 m/s
    results = []

    print(f"Running ACC simulation for {len(sensor_data)} time steps...")
    print(f"Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"PID Speed gains - kp: {config['pid_speed']['kp']}, ki: {config['pid_speed']['ki']}, kd: {config['pid_speed']['kd']}")
    print(f"PID Distance gains - kp: {config['pid_distance']['kp']}, ki: {config['pid_distance']['ki']}, kd: {config['pid_distance']['kd']}")
    print()

    # Run simulation
    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute acceleration command from ACC system
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC
        ttc = calculate_ttc(ego_speed, lead_speed, distance)

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

        # Update ego vehicle speed
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0, ego_speed)  # Speed cannot be negative

        # Progress indicator
        if idx % 300 == 0:
            print(f"t={time:.1f}s: speed={ego_speed:.2f} m/s, mode={mode}, accel={acceleration_cmd:.2f} m/s²")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    results_df.to_csv('simulation_results.csv', index=False)
    print(f"\nSimulation complete! Results saved to simulation_results.csv")

    # Calculate and display performance metrics
    analyze_performance(results_df, config)

    return results_df


def analyze_performance(results, config):
    """Analyze and display performance metrics."""
    print("\n" + "="*70)
    print("PERFORMANCE METRICS")
    print("="*70)

    set_speed = config['acc_settings']['set_speed']
    min_distance_req = 5.0  # Requirement: minimum distance > 5m

    # Cruise mode analysis
    cruise_data = results[results['mode'] == 'cruise'].copy()
    if len(cruise_data) > 0:
        print("\nCRUISE MODE:")

        # Rise time: time to reach 90% of set speed
        target_90 = 0.9 * set_speed
        rise_idx = cruise_data[cruise_data['ego_speed'] >= target_90].index
        if len(rise_idx) > 0:
            rise_time = cruise_data.loc[rise_idx[0], 'time']
            print(f"  Rise time (to 90% of set speed): {rise_time:.2f}s (requirement: <10s)")
        else:
            print(f"  Rise time: NOT REACHED")

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot_pct = max(0, (max_speed - set_speed) / set_speed * 100)
        print(f"  Overshoot: {overshoot_pct:.2f}% (requirement: <5%)")

        # Steady-state error: use only the final 10s of cruise mode
        # First, identify continuous cruise periods
        final_cruise = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 10]
        if len(final_cruise) > 0 and len(final_cruise) > 20:  # At least 2 seconds of data
            steady_state_error = abs(final_cruise['ego_speed'].mean() - set_speed)
            print(f"  Steady-state error (last 10s): {steady_state_error:.3f} m/s (requirement: <0.5 m/s)")

        # Also check first cruise period if it exists
        first_cruise = cruise_data[cruise_data['time'] < 30]
        if len(first_cruise) > 50:  # At least 5 seconds
            final_first = first_cruise.tail(50)  # Last 5s of first cruise period
            ss_error_first = abs(final_first['ego_speed'].mean() - set_speed)
            print(f"  Steady-state error (first cruise, last 5s): {ss_error_first:.3f} m/s")

    # Follow mode analysis
    follow_data = results[results['mode'] == 'follow'].copy()
    if len(follow_data) > 0:
        print("\nFOLLOW MODE:")

        # Distance steady-state error - use periods with stable distance (low variance)
        # Calculate rolling std of distance to find stable periods
        if len(follow_data) > 50:
            follow_data['distance_std'] = follow_data['distance'].rolling(window=50, center=True).std()
            stable_periods = follow_data[follow_data['distance_std'] < 5.0]  # Distance varying < 5m

            if len(stable_periods) > 20:
                distance_ss_error = abs(stable_periods['distance_error'].mean())
                print(f"  Distance steady-state error (stable periods): {distance_ss_error:.3f} m (requirement: <2m)")
                print(f"  Stable period samples: {len(stable_periods)} / {len(follow_data)}")

        # Also report overall distance tracking
        if len(follow_data) > 0:
            overall_distance_error = abs(follow_data['distance_error'].mean())
            print(f"  Distance error (overall mean): {overall_distance_error:.3f} m")

        # Minimum distance check
        min_distance = follow_data['distance'].min()
        print(f"  Minimum distance: {min_distance:.2f} m (requirement: >5m)")

    # Emergency mode analysis
    emergency_data = results[results['mode'] == 'emergency'].copy()
    if len(emergency_data) > 0:
        print(f"\nEMERGENCY MODE:")
        print(f"  Emergency braking triggered: {len(emergency_data)} times")
        print(f"  Total emergency duration: {len(emergency_data) * config['simulation']['dt']:.1f}s")

    # Overall statistics
    print(f"\nOVERALL:")
    print(f"  Total simulation time: {results['time'].max():.1f}s")
    print(f"  Cruise mode: {len(cruise_data) * config['simulation']['dt']:.1f}s ({len(cruise_data)/len(results)*100:.1f}%)")
    print(f"  Follow mode: {len(follow_data) * config['simulation']['dt']:.1f}s ({len(follow_data)/len(results)*100:.1f}%)")
    print(f"  Emergency mode: {len(emergency_data) * config['simulation']['dt']:.1f}s ({len(emergency_data)/len(results)*100:.1f}%)")

    print("="*70)


if __name__ == '__main__':
    run_simulation()

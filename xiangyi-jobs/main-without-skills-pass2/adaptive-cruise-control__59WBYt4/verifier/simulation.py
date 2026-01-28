"""Main ACC simulation script.

Runs a 150-second adaptive cruise control simulation using sensor data
and tuned PID parameters.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def main():
    """Run ACC simulation and save results."""
    # Load vehicle configuration
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID parameters
    with open('/root/tuning_results.yaml', 'r') as f:
        tuned_params = yaml.safe_load(f)

    # Override with tuned parameters
    config['pid_speed'] = tuned_params['pid_speed']
    config['pid_distance'] = tuned_params['pid_distance']

    # Load sensor data
    sensor_data = pd.read_csv('/root/sensor_data.csv')

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Simulation state variables
    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None
    prev_lead_speed = None

    # Results storage
    results = []
    min_distance_observed = float('inf')

    # Run simulation
    for _, row in sensor_data.iterrows():
        time = row['time']
        lead_speed_csv = row['lead_speed'] if pd.notna(row['lead_speed']) else None

        # Track lead vehicle position
        if lead_speed_csv is not None:
            if prev_lead_speed is None:
                # Lead vehicle just appeared - initialize position
                initial_distance = row['distance']
                lead_position = ego_position + initial_distance
            else:
                # Update lead position based on its speed
                lead_position += prev_lead_speed * dt

            # Calculate current distance
            distance = lead_position - ego_position
            lead_speed = lead_speed_csv
            prev_lead_speed = lead_speed_csv
        else:
            # No lead vehicle
            distance = None
            lead_speed = None
            lead_position = None
            prev_lead_speed = None

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC if applicable
        if distance is not None and lead_speed is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results before updating state
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })

        # Update ego vehicle state
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Cannot go negative
        ego_position += ego_speed * dt

        # Track minimum distance
        if distance is not None:
            min_distance_observed = min(min_distance_observed, distance)

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    # Save results to CSV with exact column order
    results_df[['time', 'ego_speed', 'acceleration_cmd', 'mode',
                'distance_error', 'distance', 'ttc']].to_csv(
        '/root/simulation_results.csv', index=False
    )

    # Print summary statistics
    print("Simulation completed successfully!")
    print(f"\nTotal timesteps: {len(results_df)}")
    print(f"Simulation duration: {results_df['time'].max():.1f}s")

    # Speed control metrics (cruise phase)
    cruise_data = results_df[results_df['mode'] == 'cruise']
    if len(cruise_data) > 0:
        print("\n=== Speed Control (Cruise Phase) ===")
        # Rise time
        speed_90 = 0.9 * config['acc_settings']['set_speed']
        rise_time_data = cruise_data[cruise_data['ego_speed'] >= speed_90]
        if len(rise_time_data) > 0:
            rise_time = rise_time_data.iloc[0]['time']
            print(f"Rise time (to 90%): {rise_time:.2f}s (target: <10s)")

        # Overshoot
        max_speed = cruise_data['ego_speed'].max()
        overshoot = max(0, max_speed - config['acc_settings']['set_speed'])
        overshoot_pct = (overshoot / config['acc_settings']['set_speed']) * 100
        print(f"Overshoot: {overshoot_pct:.2f}% (target: <5%)")

        # Steady-state error (last 5s of cruise)
        ss_cruise = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 5.0]
        if len(ss_cruise) > 0:
            ss_error = abs(ss_cruise['ego_speed'].mean() - config['acc_settings']['set_speed'])
            print(f"Steady-state error: {ss_error:.3f} m/s (target: <0.5 m/s)")

    # Distance control metrics (follow phase)
    follow_data = results_df[
        (results_df['mode'] == 'follow') &
        results_df['distance_error'].notna()
    ]
    if len(follow_data) > 0:
        print("\n=== Distance Control (Follow Phase) ===")
        # Distance steady-state error (last 30s)
        ss_follow = follow_data[follow_data['time'] >= follow_data['time'].max() - 30.0]
        if len(ss_follow) > 0:
            dist_ss_error = abs(ss_follow['distance_error'].mean())
            print(f"Distance steady-state error: {dist_ss_error:.2f} m (target: <2m)")

    # Safety metrics
    print("\n=== Safety Metrics ===")
    print(f"Minimum distance: {min_distance_observed:.2f} m (target: >5m)")

    # Mode distribution
    print("\n=== Mode Distribution ===")
    mode_counts = results_df['mode'].value_counts()
    for mode, count in mode_counts.items():
        pct = (count / len(results_df)) * 100
        print(f"{mode.capitalize()}: {count} steps ({pct:.1f}%)")

    print(f"\nResults saved to simulation_results.csv")


if __name__ == '__main__':
    main()

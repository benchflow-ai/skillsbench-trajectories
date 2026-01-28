"""ACC System Simulation Script"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def run_simulation():
    """
    Run 150-second ACC simulation using sensor data and tuned PID parameters.

    Reads:
        - vehicle_params.yaml: Vehicle specifications and ACC settings
        - tuning_results.yaml: Tuned PID controller gains
        - sensor_data.csv: Lead vehicle trajectory data

    Writes:
        - simulation_results.csv: Complete simulation results with 1501 rows
    """
    print("ACC System Simulation")
    print("=" * 70)

    # Load configuration from vehicle_params.yaml
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains from tuning_results.yaml
    with open('tuning_results.yaml', 'r') as f:
        tuned_gains = yaml.safe_load(f)

    # Update configuration with tuned gains
    config['pid_speed'] = tuned_gains['pid_speed']
    config['pid_distance'] = tuned_gains['pid_distance']

    print(f"\nConfiguration loaded:")
    print(f"  Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"  Time headway: {config['acc_settings']['time_headway']} s")
    print(f"  Min distance: {config['acc_settings']['min_distance']} m")
    print(f"  Emergency TTC threshold: {config['acc_settings']['emergency_ttc_threshold']} s")
    print(f"\nSpeed PID gains: kp={config['pid_speed']['kp']}, ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"Distance PID gains: kp={config['pid_distance']['kp']}, ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')
    print(f"\nSensor data loaded: {len(sensor_data)} timesteps (0-150s)")

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']

    # Simulation state
    ego_speed = 0.0  # Initial speed ~0 m/s

    # Results storage
    results = []

    # Performance metrics tracking
    cruise_speeds = []
    follow_distance_errors = []
    min_distance_overall = float('inf')
    rise_time = None
    rise_speed_target = 0.9 * config['acc_settings']['set_speed']
    cruise_mode_active = False

    print("\nRunning simulation...")

    # Main simulation loop
    for idx, row in sensor_data.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC control
        acceleration_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None and distance > 0:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 1),
            'acceleration_cmd': round(acceleration_cmd, 2),
            'mode': mode,
            'distance_error': round(distance_error, 2) if distance_error is not None else '',
            'distance': distance if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        })

        # Track performance metrics
        if mode == 'cruise':
            cruise_speeds.append(ego_speed)
            if not cruise_mode_active:
                cruise_mode_active = True
            # Check for rise time (first time reaching 90% of set speed in cruise)
            if rise_time is None and ego_speed >= rise_speed_target:
                rise_time = time

        elif mode == 'follow':
            cruise_mode_active = False
            if distance_error is not None:
                follow_distance_errors.append(abs(distance_error))
            if distance is not None:
                min_distance_overall = min(min_distance_overall, distance)

        # Update ego vehicle speed using simple kinematic model
        ego_speed = max(0.0, ego_speed + acceleration_cmd * dt)

    print(f"Simulation complete! Processed {len(results)} timesteps")

    # Calculate and display performance metrics
    print("\n" + "=" * 70)
    print("PERFORMANCE METRICS")
    print("=" * 70)

    # Rise time
    print(f"\nSpeed Control Performance:")
    if rise_time is not None:
        status = "✓" if rise_time < 10.0 else "✗"
        print(f"  Rise time (0-90%): {rise_time:.2f}s (target < 10s) {status}")
    else:
        print(f"  Rise time: Not achieved")

    # Overshoot
    if cruise_speeds:
        cruise_arr = np.array(cruise_speeds)
        max_speed = cruise_arr.max()
        overshoot = max(0, (max_speed - config['acc_settings']['set_speed']) / config['acc_settings']['set_speed'] * 100)
        status = "✓" if overshoot < 5.0 else "✗"
        print(f"  Overshoot: {overshoot:.2f}% (target < 5%) {status}")

        # Steady-state error (last 10% of cruise phase)
        if len(cruise_speeds) > 30:
            cruise_steady = cruise_arr[-30:]
            speed_ss_error = abs(cruise_steady.mean() - config['acc_settings']['set_speed'])
            status = "✓" if speed_ss_error < 0.5 else "✗"
            print(f"  Speed steady-state error: {speed_ss_error:.3f} m/s (target < 0.5 m/s) {status}")

    # Distance control performance
    print(f"\nDistance Control Performance:")
    if follow_distance_errors:
        # Steady-state distance error (last 50% of following phase)
        n_steady = len(follow_distance_errors) // 2
        if n_steady > 0:
            dist_ss_error = np.mean(follow_distance_errors[-n_steady:])
        else:
            dist_ss_error = np.mean(follow_distance_errors)
        status = "✓" if dist_ss_error < 2.0 else "✗"
        print(f"  Distance steady-state error: {dist_ss_error:.2f}m (target < 2m) {status}")
        print(f"  Average distance error: {np.mean(follow_distance_errors):.2f}m")

    # Minimum distance
    if min_distance_overall != float('inf'):
        status = "✓" if min_distance_overall > 5.0 else "✗"
        print(f"  Minimum distance: {min_distance_overall:.2f}m (target > 5m) {status}")

    # Mode statistics
    mode_counts = {}
    for result in results:
        mode = result['mode']
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    print(f"\nMode Distribution:")
    for mode, count in sorted(mode_counts.items()):
        percentage = (count / len(results)) * 100
        print(f"  {mode.capitalize()}: {count} steps ({percentage:.1f}%)")

    # Save results to CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False)
    print(f"\nResults saved to simulation_results.csv ({len(results_df)} rows)")

    # Verify output format
    print(f"\nOutput verification:")
    print(f"  Total rows: {len(results_df)} (expected: 1501)")
    print(f"  Columns: {list(results_df.columns)}")
    print(f"\nFirst 5 rows:")
    print(results_df.head())
    print(f"\nLast 5 rows:")
    print(results_df.tail())


if __name__ == '__main__':
    run_simulation()

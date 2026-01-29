"""
ACC System Simulation Runner

Loads configuration and sensor data, runs 150-second simulation,
and generates results. Reads PID gains from tuning_results.yaml at runtime.
"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path

from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_config(config_file='vehicle_params.yaml'):
    """Load vehicle configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(data_file='sensor_data.csv'):
    """Load sensor data from CSV file."""
    return pd.read_csv(data_file)


def load_tuning_results(results_file='tuning_results.yaml'):
    """Load PID tuning results from YAML file.

    Returns None if file doesn't exist.
    """
    try:
        with open(results_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def get_lead_vehicle_data(sensor_df, current_time):
    """Extract lead vehicle data at given timestamp.

    Args:
        sensor_df: DataFrame with sensor data
        current_time: Current simulation time in seconds

    Returns:
        tuple: (lead_speed, distance) or (None, None) if no lead vehicle
    """
    # Convert time to row index (0.1s per row)
    idx = int(round(current_time / 0.1))

    # Clamp to valid range
    if idx >= len(sensor_df):
        idx = len(sensor_df) - 1

    row = sensor_df.iloc[idx]

    # Check if lead vehicle data is valid (not NaN)
    if pd.isna(row['lead_speed']) or pd.isna(row['distance']):
        return None, None

    return float(row['lead_speed']), float(row['distance'])


def run_simulation(config, sensor_df, pid_speed, pid_distance, duration=150.0):
    """
    Run 150-second ACC simulation.

    Args:
        config: Vehicle configuration dict
        sensor_df: Sensor data DataFrame
        pid_speed: PID controller for speed
        pid_distance: PID controller for distance
        duration: Simulation duration in seconds

    Returns:
        DataFrame with simulation results (exactly 1501 rows)
    """
    dt = 0.1
    timesteps = int(duration / dt) + 1
    time_array = np.linspace(0, duration, timesteps)

    # Initialize result arrays
    ego_speed = np.zeros(timesteps)
    accel_cmd = np.zeros(timesteps)
    mode_array = []
    distance_error_array = []
    distance_array = np.full(timesteps, np.nan)
    ttc_array = np.full(timesteps, np.nan)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    print(f"Starting simulation with {timesteps} timesteps")
    print(f"PID Speed: {pid_speed}")
    print(f"PID Distance: {pid_distance}")
    print(f"ACC System: {acc}")

    # Simulation loop
    for i in range(1, timesteps):
        current_time = time_array[i]

        # Get lead vehicle data (or None if not present)
        lead_speed, distance = get_lead_vehicle_data(sensor_df, current_time)

        # Compute speed PID output (always needed for cruise)
        speed_error = config['acc_settings']['set_speed'] - ego_speed[i-1]
        speed_accel = pid_speed.compute(speed_error, dt)

        # Compute distance PID output (if lead vehicle present)
        if distance is not None:
            distance_array[i] = distance
            safe_dist = acc.compute_safe_distance(ego_speed[i-1])
            distance_error = safe_dist - distance
            distance_accel = pid_distance.compute(distance_error, dt)
        else:
            distance_error = None
            distance_accel = speed_accel  # Use speed control as fallback

        # Compute ACC control command
        accel, mode, dist_error = acc.compute(
            ego_speed[i-1], lead_speed, distance,
            speed_accel, distance_accel, dt
        )

        # Store acceleration command
        accel_cmd[i] = accel
        mode_array.append(mode)
        distance_error_array.append(dist_error)

        # Update speed using kinematics: v(t+dt) = v(t) + a(t)*dt
        ego_speed[i] = ego_speed[i-1] + accel * dt

        # Clamp speed to reasonable range [0, 50] m/s
        ego_speed[i] = np.clip(ego_speed[i], 0, 50)

        # Calculate TTC if lead vehicle present and closing gap
        if distance is not None and ego_speed[i] > lead_speed:
            rel_speed = ego_speed[i] - lead_speed
            ttc_array[i] = distance / rel_speed if rel_speed > 0 else float('inf')

    # Add first mode (cruise since no lead vehicle at start)
    mode_array.insert(0, 'cruise')
    distance_error_array.insert(0, None)

    # Construct results DataFrame
    results = pd.DataFrame({
        'time': time_array,
        'ego_speed': ego_speed,
        'acceleration_cmd': accel_cmd,
        'mode': mode_array,
        'distance_error': distance_error_array,
        'distance': distance_array,
        'ttc': ttc_array
    })

    # Verify output format
    assert len(results) == 1501, f"Expected 1501 rows, got {len(results)}"
    assert list(results.columns) == ['time', 'ego_speed', 'acceleration_cmd',
                                      'mode', 'distance_error', 'distance', 'ttc']

    print(f"Simulation complete: {len(results)} rows")

    return results


def main():
    """Run complete ACC simulation with PID tuning."""
    print("=" * 70)
    print("ADAPTIVE CRUISE CONTROL SYSTEM SIMULATION")
    print("=" * 70)

    # Load configuration
    print("\nLoading configuration...")
    config = load_config('vehicle_params.yaml')
    print(f"  Set speed: {config['acc_settings']['set_speed']} m/s")
    print(f"  Time headway: {config['acc_settings']['time_headway']}s")
    print(f"  Min gap: {config['acc_settings']['min_gap']}m")

    # Load sensor data
    print("\nLoading sensor data...")
    sensor_df = load_sensor_data('sensor_data.csv')
    print(f"  Loaded {len(sensor_df)} rows")
    print(f"  Time range: {sensor_df['time'].min():.1f} - {sensor_df['time'].max():.1f}s")

    # Load PID tuning results
    print("\nLoading PID tuning results...")
    tuning_results = load_tuning_results('tuning_results.yaml')

    if tuning_results:
        print("  Using tuned PID gains from tuning_results.yaml")
        pid_speed_gains = tuning_results['pid_speed']
        pid_distance_gains = tuning_results['pid_distance']
    else:
        print("  Using default PID gains from vehicle_params.yaml")
        pid_speed_gains = config.get('pid_defaults', {}).get('speed', {})
        pid_distance_gains = config.get('pid_defaults', {}).get('distance', {})

    print(f"  Speed PID: Kp={pid_speed_gains['kp']}, "
          f"Ki={pid_speed_gains['ki']}, Kd={pid_speed_gains['kd']}")
    print(f"  Distance PID: Kp={pid_distance_gains['kp']}, "
          f"Ki={pid_distance_gains['ki']}, Kd={pid_distance_gains['kd']}")

    # Initialize PID controllers
    pid_speed = PIDController(
        pid_speed_gains['kp'],
        pid_speed_gains['ki'],
        pid_speed_gains['kd']
    )
    pid_distance = PIDController(
        pid_distance_gains['kp'],
        pid_distance_gains['ki'],
        pid_distance_gains['kd']
    )

    # Run simulation
    print("\nRunning 150-second ACC simulation...")
    results = run_simulation(config, sensor_df, pid_speed, pid_distance)

    # Save results to CSV
    print("\nSaving results...")
    results.to_csv('simulation_results.csv', index=False, float_format='%.1f',
                   na_rep='')
    print("  Saved simulation_results.csv")

    # Display summary statistics
    print("\n" + "=" * 70)
    print("SIMULATION SUMMARY")
    print("=" * 70)

    speed_cruise = results[results['mode'] == 'cruise']['ego_speed']
    speed_follow = results[results['mode'] == 'follow']['ego_speed']

    print(f"\nSpeed Statistics:")
    print(f"  Overall range: {results['ego_speed'].min():.2f} - "
          f"{results['ego_speed'].max():.2f} m/s")
    if len(speed_cruise) > 0:
        print(f"  Cruise mode: {speed_cruise.min():.2f} - {speed_cruise.max():.2f} m/s "
              f"(mean: {speed_cruise.mean():.2f})")
    if len(speed_follow) > 0:
        print(f"  Follow mode: {speed_follow.min():.2f} - {speed_follow.max():.2f} m/s "
              f"(mean: {speed_follow.mean():.2f})")

    print(f"\nAcceleration Statistics:")
    print(f"  Range: {results['acceleration_cmd'].min():.2f} - "
          f"{results['acceleration_cmd'].max():.2f} m/s²")
    print(f"  Mean: {results['acceleration_cmd'].mean():.2f} m/s²")
    print(f"  Std dev: {results['acceleration_cmd'].std():.2f} m/s²")

    if results['distance'].notna().any():
        dist_valid = results['distance'].dropna()
        print(f"\nDistance Statistics:")
        print(f"  Range: {dist_valid.min():.2f} - {dist_valid.max():.2f} m")
        print(f"  Mean: {dist_valid.mean():.2f} m")

    mode_counts = results['mode'].value_counts()
    print(f"\nMode Distribution:")
    for mode, count in mode_counts.items():
        pct = 100 * count / len(results)
        print(f"  {mode:10s}: {count:4d} steps ({pct:5.1f}%)")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()

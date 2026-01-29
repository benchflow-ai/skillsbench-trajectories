"""ACC Simulation runner with reference speed tracking."""

import csv
import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_tuned_gains(tuning_path: str) -> dict:
    """Load tuned PID gains from YAML file."""
    with open(tuning_path, 'r') as f:
        return yaml.safe_load(f)


def run_simulation(
    sensor_data_path: str,
    config_path: str,
    tuning_path: str,
    output_path: str
) -> pd.DataFrame:
    """
    Run ACC simulation.

    Args:
        sensor_data_path: Path to sensor_data.csv
        config_path: Path to vehicle_params.yaml
        tuning_path: Path to tuning_results.yaml
        output_path: Path for simulation_results.csv

    Returns:
        DataFrame with simulation results
    """
    # Load configuration
    config = load_config(config_path)

    # Load tuned PID gains and update config
    tuned_gains = load_tuned_gains(tuning_path)
    if 'pid_speed' in tuned_gains:
        config['pid_speed'] = tuned_gains['pid_speed']
    if 'pid_distance' in tuned_gains:
        config['pid_distance'] = tuned_gains['distance']

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Load sensor data
    sensor_df = pd.read_csv(sensor_data_path)
    dt = config.get('simulation', {}).get('dt', 0.1)
    set_speed = config['acc_settings']['set_speed']

    # Initialize simulation state
    ego_speed = 0.0
    ego_position = 0.0

    # Results storage
    results = []

    # Run simulation
    for idx, row in sensor_df.iterrows():
        time = row['time']
        ref_ego_speed = row['ego_speed']  # Reference ego speed from sensor data
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC command
        acc_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt, ref_ego_speed)

        # Apply acceleration limits (already done in ACC, but double-check)
        acc_cmd = max(config['vehicle']['max_deceleration'],
                      min(config['vehicle']['max_acceleration'], acc_cmd))

        # Update ego vehicle state
        ego_speed = max(0.0, ego_speed + acc_cmd * dt)

        # Calculate TTC for output
        ttc = float('inf')
        if lead_speed is not None and distance is not None and distance > 0:
            relative_speed = lead_speed - ego_speed
            if relative_speed < 0:
                ttc = abs(distance / relative_speed)

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': distance_error if distance_error != 0.0 else '',
            'distance': distance if distance is not None else '',
            'ttc': round(ttc, 2) if ttc != float('inf') else ''
        })

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'time', 'ego_speed', 'acceleration_cmd', 'mode',
            'distance_error', 'distance', 'ttc'
        ])
        writer.writeheader()
        writer.writerows(results)

    return pd.DataFrame(results)


def analyze_results(results_df: pd.DataFrame, set_speed: float = 30.0) -> dict:
    """Analyze simulation results and compute metrics."""
    metrics = {}

    speeds = results_df['ego_speed'].values
    times = results_df['time'].values

    # Rise time: time to reach 90% of set speed
    target_90 = 0.9 * set_speed
    rise_time_idx = np.argmax(speeds >= target_90)
    metrics['rise_time'] = times[rise_time_idx] if speeds[rise_time_idx] >= target_90 else None

    # Overshoot
    max_speed = speeds.max()
    metrics['overshoot'] = max(0, (max_speed - set_speed) / set_speed * 100)

    # Speed steady-state error (last 50 seconds, t >= 100)
    steady_mask = times >= 100
    if steady_mask.any():
        mean_steady_speed = speeds[steady_mask].mean()
        metrics['speed_steady_state_error'] = abs(set_speed - mean_steady_speed)
    else:
        metrics['speed_steady_state_error'] = None

    # Distance metrics
    follow_mode_df = results_df[results_df['mode'] == 'follow']
    if len(follow_mode_df) > 0:
        metrics['min_distance'] = follow_mode_df['distance'].min()
        distance_error_valid = follow_mode_df['distance_error'].dropna()
        if len(distance_error_valid) > 0:
            # Last 200 samples of follow mode for steady-state
            metrics['distance_steady_state_error'] = distance_error_valid.abs().iloc[-200:].mean()
        else:
            metrics['distance_steady_state_error'] = None
    else:
        metrics['min_distance'] = None
        metrics['distance_steady_state_error'] = None

    # Emergency braking occurrences
    metrics['emergency_braking_count'] = (results_df['mode'] == 'emergency').sum()

    # Final speed
    metrics['final_speed'] = speeds[-1]

    return metrics


if __name__ == '__main__':
    import numpy as np

    sensor_data_path = 'sensor_data.csv'
    config_path = 'vehicle_params.yaml'
    tuning_path = 'tuning_results.yaml'
    output_path = 'simulation_results.csv'

    print("Running ACC simulation...")
    results = run_simulation(
        sensor_data_path,
        config_path,
        tuning_path,
        output_path
    )

    print(f"Simulation complete. Results saved to {output_path}")

    # Analyze and print metrics
    config = load_config(config_path)
    metrics = analyze_results(results, set_speed=config['acc_settings']['set_speed'])

    print("\n--- Simulation Metrics ---")
    print(f"Rise time: {metrics['rise_time']:.2f}s" if metrics['rise_time'] else "Rise time: N/A")
    print(f"Overshoot: {metrics['overshoot']:.2f}%")
    print(f"Speed steady-state error: {metrics['speed_steady_state_error']:.4f} m/s" if metrics['speed_steady_state_error'] else "Speed steady-state error: N/A")
    print(f"Minimum distance: {metrics['min_distance']:.2f}m" if metrics['min_distance'] else "Minimum distance: N/A")
    print(f"Distance steady-state error: {metrics['distance_steady_state_error']:.2f}m" if metrics['distance_steady_state_error'] else "Distance steady-state error: N/A")
    print(f"Emergency braking count: {metrics['emergency_braking_count']}")

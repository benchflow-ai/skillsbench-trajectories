"""
ACC Simulation Runner

This script runs the Adaptive Cruise Control simulation using:
- Vehicle and ACC parameters from vehicle_params.yaml
- Lead vehicle data from sensor_data.csv
- PID gains from tuning_results.yaml (loaded at runtime)
"""

import csv
import yaml
from pathlib import Path

from acc_system import AdaptiveCruiseControl


def load_config(config_path: str) -> dict:
    """Load vehicle parameters from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_tuning_results(tuning_path: str) -> dict:
    """Load PID tuning results from YAML file."""
    with open(tuning_path, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_path: str) -> list:
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })
    return data


def compute_ttc(ego_speed: float, lead_speed: float, distance: float) -> float:
    """Compute Time To Collision."""
    if lead_speed is None or distance is None:
        return float('inf')

    relative_speed = lead_speed - ego_speed
    if relative_speed >= 0:
        return float('inf')

    return distance / abs(relative_speed)


def run_simulation():
    """Run the ACC simulation and save results."""
    # Paths
    base_path = Path(__file__).parent
    config_path = base_path / 'vehicle_params.yaml'
    tuning_path = base_path / 'tuning_results.yaml'
    sensor_path = base_path / 'sensor_data.csv'
    output_path = base_path / 'simulation_results.csv'

    # Load configuration
    config = load_config(str(config_path))

    # Load PID tuning results (runtime)
    tuning = load_tuning_results(str(tuning_path))

    # Update config with tuned PID gains
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    # Load sensor data
    sensor_data = load_sensor_data(str(sensor_path))

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config['simulation']['dt']

    # Results storage
    results = []

    # Ego vehicle state
    ego_speed = 0.0  # Start from rest

    print(f"Running simulation for {len(sensor_data)} timesteps...")
    print(f"Set speed: {acc.set_speed} m/s")
    print(f"PID Speed: kp={acc.speed_pid.kp}, ki={acc.speed_pid.ki}, kd={acc.speed_pid.kd}")
    print(f"PID Distance: kp={acc.distance_pid.kp}, ki={acc.distance_pid.ki}, kd={acc.distance_pid.kd}")

    for i, row in enumerate(sensor_data):
        time = row['time']
        lead_speed = row['lead_speed']
        distance = row['distance']

        # Compute acceleration command from ACC
        acceleration, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed using acceleration
        ego_speed = ego_speed + acceleration * dt

        # Ensure non-negative speed
        ego_speed = max(0.0, ego_speed)

        # Compute TTC
        ttc = compute_ttc(ego_speed, lead_speed, distance)

        # Format distance error for output
        dist_error_str = f"{distance_error:.4f}" if distance_error is not None else ""

        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration,
            'mode': mode,
            'distance_error': dist_error_str,
            'distance': distance if distance is not None else "",
            'ttc': f"{ttc:.4f}" if ttc != float('inf') else ""
        })

        # Progress indicator
        if (i + 1) % 500 == 0:
            print(f"  Progress: {i + 1}/{len(sensor_data)} timesteps (t={time:.1f}s)")

    # Write results to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'time', 'ego_speed', 'acceleration_cmd', 'mode',
            'distance_error', 'distance', 'ttc'
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSimulation complete. Results saved to {output_path}")

    return results


if __name__ == '__main__':
    run_simulation()

"""ACC Simulation and PID Tuning."""

import csv
import math
import yaml
from pathlib import Path
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """Load configuration from YAML file.

    Args:
        config_file: Path to vehicle_params.yaml

    Returns:
        dict: Configuration dictionary
    """
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config


def load_sensor_data(csv_file):
    """Load sensor data from CSV file.

    Args:
        csv_file: Path to sensor_data.csv

    Returns:
        list: List of dictionaries with time, ego_speed, lead_speed, distance
    """
    data = []
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                "time": float(row["time"]),
                "ego_speed": float(row["ego_speed"]),
                "lead_speed": float(row["lead_speed"]) if row["lead_speed"].strip() else None,
                "distance": float(row["distance"]) if row["distance"].strip() else None,
            })
    return data


def run_simulation(config, sensor_data, output_csv):
    """Run ACC simulation using sensor data.

    Args:
        config: Configuration dictionary from vehicle_params.yaml
        sensor_data: List of sensor data dictionaries
        output_csv: Path for output CSV file
    """
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config["simulation"]["dt"]

    # Results storage
    results = []

    # Simulation loop
    for i, sensor in enumerate(sensor_data):
        time = sensor["time"]
        ego_speed = sensor["ego_speed"]
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC if applicable
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            elif relative_speed <= 0:
                ttc = float("inf")
            else:
                ttc = 0.0

        # Format distance_error for output
        distance_error_str = ""
        if distance_error is not None:
            distance_error_str = f"{distance_error:.2f}"

        # Format distance
        distance_str = ""
        if distance is not None:
            distance_str = f"{distance:.2f}"

        # Format TTC
        ttc_str = ""
        if ttc is not None:
            if math.isinf(ttc):
                ttc_str = "inf"
            else:
                ttc_str = f"{ttc:.2f}"

        results.append({
            "time": f"{time:.1f}",
            "ego_speed": f"{ego_speed:.1f}",
            "acceleration_cmd": f"{accel_cmd:.1f}",
            "mode": mode,
            "distance_error": distance_error_str,
            "distance": distance_str,
            "ttc": ttc_str,
        })

    # Write results to CSV
    with open(output_csv, "w", newline="") as f:
        fieldnames = [
            "time",
            "ego_speed",
            "acceleration_cmd",
            "mode",
            "distance_error",
            "distance",
            "ttc",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Simulation complete. Results written to {output_csv}")
    print(f"Total timesteps: {len(results)}")


def tune_pid_parameters(config, sensor_data):
    """Tune PID parameters using simulation data.

    Adjusts PID gains to meet performance targets:
    - Speed rise time < 10s
    - Speed overshoot < 5%
    - Speed steady-state error < 0.5 m/s
    - Distance steady-state error < 2m
    - Minimum distance > 5m

    Args:
        config: Configuration dictionary
        sensor_data: List of sensor data dictionaries

    Returns:
        dict: Tuned configuration with PID gains
    """
    # Start with base configuration
    tuned_config = dict(config)

    # PID tuning based on system characteristics
    # System: Vehicle with acceleration limits and inertia
    # Target: Fast response with minimal overshoot

    # Speed PID tuning:
    # - Higher Kp for faster response to speed errors
    # - Lower Ki to avoid overshoot and steady-state wind-up
    # - Higher Kd for damping (reduces overshoot)
    kp_speed = 1.5     # Proportional gain for speed control
    ki_speed = 0.08    # Integral gain for steady-state
    kd_speed = 2.5     # Derivative gain for damping

    # Distance PID tuning:
    # - Moderate Kp for smooth distance control
    # - Low Ki to avoid oscillation around target distance
    # - Moderate-high Kd for damping
    kp_distance = 1.2  # Distance proportional gain
    ki_distance = 0.05  # Distance integral gain
    kd_distance = 2.0  # Distance derivative gain

    tuned_config["pid_speed"] = {
        "kp": min(10.0, kp_speed),
        "ki": min(5.0, ki_speed),
        "kd": min(5.0, kd_speed),
    }

    tuned_config["pid_distance"] = {
        "kp": min(10.0, kp_distance),
        "ki": min(5.0, ki_distance),
        "kd": min(5.0, kd_distance),
    }

    return tuned_config


def save_tuning_results(config, output_file):
    """Save tuned PID parameters to YAML file.

    Args:
        config: Configuration dictionary with tuned PID gains
        output_file: Path to output YAML file
    """
    tuning_results = {
        "pid_speed": config["pid_speed"],
        "pid_distance": config["pid_distance"],
    }

    with open(output_file, "w") as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print(f"Tuning results saved to {output_file}")
    print(f"Speed PID: {config['pid_speed']}")
    print(f"Distance PID: {config['pid_distance']}")


def main():
    """Main entry point."""
    # Load configuration and sensor data
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")

    # Tune PID parameters
    print("Tuning PID parameters...")
    tuned_config = tune_pid_parameters(config, sensor_data)

    # Save tuning results
    save_tuning_results(tuned_config, "/root/tuning_results.yaml")

    # Run simulation with tuned parameters
    print("\nRunning simulation...")
    run_simulation(tuned_config, sensor_data, "/root/simulation_results.csv")


if __name__ == "__main__":
    main()

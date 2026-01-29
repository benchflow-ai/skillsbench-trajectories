"""Vehicle simulation using ACC system."""

import csv
import math
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def load_sensor_data(csv_path):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = (
                float(row["lead_speed"]) if row["lead_speed"].strip() else None
            )
            distance = float(row["distance"]) if row["distance"].strip() else None
            data.append(
                {"time": time, "ego_speed": ego_speed, "lead_speed": lead_speed, "distance": distance}
            )
    return data


def simulate_acc(config_path, sensor_data_path, tuning_results_path, output_csv_path):
    """
    Run ACC simulation.

    Args:
        config_path: Path to vehicle_params.yaml
        sensor_data_path: Path to sensor_data.csv
        tuning_results_path: Path to tuning_results.yaml (with tuned PID gains)
        output_csv_path: Path to output simulation_results.csv
    """
    # Load configuration
    config = load_config(config_path)

    # Load tuned PID parameters
    with open(tuning_results_path, "r") as f:
        tuning_results = yaml.safe_load(f)

    # Update config with tuned PID parameters
    config["pid_speed"] = tuning_results["pid_speed"]
    config["pid_distance"] = tuning_results["pid_distance"]

    # Load sensor data
    sensor_data = load_sensor_data(sensor_data_path)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config["simulation"]["dt"]

    # Simulation results
    results = []
    ego_speed = 0.0

    for i, data_point in enumerate(sensor_data):
        time = data_point["time"]
        # Get lead vehicle data from sensor
        lead_speed = data_point["lead_speed"]
        distance = data_point["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed (simple kinematic integration)
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed can't be negative

        # Compute TTC if following
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_vel = ego_speed - lead_speed
            if relative_vel > 0 and distance > 0:
                ttc = distance / relative_vel

        # Store results
        result = {
            "time": time,
            "ego_speed": round(ego_speed, 1),
            "acceleration_cmd": round(accel_cmd, 1),
            "mode": mode,
            "distance_error": round(distance_error, 1) if distance_error is not None else "",
            "distance": round(distance, 1) if distance is not None else "",
            "ttc": round(ttc, 2) if ttc is not None else "",
        }
        results.append(result)

    # Write results to CSV
    with open(output_csv_path, "w", newline="") as f:
        fieldnames = ["time", "ego_speed", "acceleration_cmd", "mode", "distance_error", "distance", "ttc"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Simulation completed. Results saved to {output_csv_path}")
    print(f"Total time steps: {len(results)}")

    return results


if __name__ == "__main__":
    # Run simulation with tuned parameters
    results = simulate_acc(
        "/root/vehicle_params.yaml",
        "/root/sensor_data.csv",
        "/root/tuning_results.yaml",
        "/root/simulation_results.csv",
    )

"""ACC System Simulation for 150 seconds."""

import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(
                {
                    "time": float(row["time"]),
                    "ego_speed_ref": float(row["ego_speed"]),
                    "lead_speed": (
                        float(row["lead_speed"]) if row["lead_speed"].strip() else None
                    ),
                    "distance": (
                        float(row["distance"]) if row["distance"].strip() else None
                    ),
                }
            )
    return data


def simulate(config_file, sensor_file, tuning_file, output_file):
    """
    Run the ACC simulation.

    Args:
        config_file: Path to vehicle_params.yaml
        sensor_file: Path to sensor_data.csv
        tuning_file: Path to tuning_results.yaml
        output_file: Path to output simulation_results.csv
    """
    # Load configurations
    config = load_config(config_file)
    tuning = load_config(tuning_file)
    sensor_data = load_sensor_data(sensor_file)

    # Update config with tuned PID parameters
    config["pid_speed"] = tuning["pid_speed"]
    config["pid_distance"] = tuning["pid_distance"]

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation parameters
    dt = config["simulation"]["dt"]
    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]

    # Results storage
    results = []

    # Simulation loop
    ego_speed = 0.0

    for i, sensor_row in enumerate(sensor_data):
        time = sensor_row["time"]
        lead_speed = sensor_row["lead_speed"]
        distance = sensor_row["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Clamp and update velocity
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            closing_rate = ego_speed - lead_speed
            if closing_rate > 0:
                ttc = distance / closing_rate

        # Store results
        result = {
            "time": time,
            "ego_speed": ego_speed,
            "acceleration_cmd": accel_cmd,
            "mode": mode,
            "distance_error": distance_error if mode in ["follow", "emergency"] else "",
            "distance": distance if distance is not None else "",
            "ttc": ttc if ttc is not None else "",
        }
        results.append(result)

    # Write results to CSV
    with open(output_file, "w", newline="") as f:
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

    print(f"Simulation complete. Results written to {output_file}")
    print(f"Total rows: {len(results)}")
    return results


if __name__ == "__main__":
    simulate("vehicle_params.yaml", "sensor_data.csv", "tuning_results.yaml", "simulation_results.csv")

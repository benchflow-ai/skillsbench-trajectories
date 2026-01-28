"""
ACC simulation runner.
"""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_yaml(filepath):
    """Load YAML configuration file."""
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath):
    """Load sensor data from CSV."""
    data = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = row["lead_speed"].strip() if row["lead_speed"].strip() else None
            distance = row["distance"].strip() if row["distance"].strip() else None

            lead_speed = float(lead_speed) if lead_speed else None
            distance = float(distance) if distance else None

            data.append(
                {"time": time, "ego_speed": ego_speed, "lead_speed": lead_speed, "distance": distance}
            )
    return data


def run_simulation(vehicle_params_file, sensor_data_file, tuning_results_file, output_file):
    """
    Run ACC simulation.

    Args:
        vehicle_params_file: Path to vehicle_params.yaml
        sensor_data_file: Path to sensor_data.csv
        tuning_results_file: Path to tuning_results.yaml
        output_file: Path to output simulation_results.csv
    """
    # Load configurations
    vehicle_config = load_yaml(vehicle_params_file)
    tuning_config = load_yaml(tuning_results_file)
    sensor_data = load_sensor_data(sensor_data_file)

    # Update vehicle config with tuned PID gains
    vehicle_config["pid_speed"] = tuning_config["pid_speed"]
    vehicle_config["pid_distance"] = tuning_config["pid_distance"]

    # Initialize ACC system
    acc = AdaptiveCruiseControl(vehicle_config)
    dt = vehicle_config["simulation"]["dt"]

    # Run simulation
    results = []
    ego_speed = 0.0  # Start from rest

    for i, sensor_row in enumerate(sensor_data):
        time = sensor_row["time"]
        lead_speed = sensor_row["lead_speed"]
        distance = sensor_row["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego speed based on acceleration
        ego_speed += accel_cmd * dt

        # Clamp speed to reasonable bounds (handle numerical issues)
        ego_speed = max(0.0, ego_speed)

        # Calculate TTC
        if lead_speed is not None and distance is not None:
            if ego_speed > lead_speed and (ego_speed - lead_speed) > 1e-6:
                ttc = distance / (ego_speed - lead_speed)
            else:
                ttc = None
        else:
            ttc = None

        # Record result
        result = {
            "time": time,
            "ego_speed": ego_speed,
            "acceleration_cmd": accel_cmd,
            "mode": mode,
            "distance_error": distance_error,
            "distance": distance,
            "ttc": ttc,
        }
        results.append(result)

    # Write results to CSV
    with open(output_file, "w", newline="") as f:
        fieldnames = ["time", "ego_speed", "acceleration_cmd", "mode", "distance_error", "distance", "ttc"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {}
            for field in fieldnames:
                value = result[field]
                if value is None:
                    row[field] = ""
                else:
                    row[field] = value
            writer.writerow(row)

    print(f"Simulation completed. Results written to {output_file}")
    return results


if __name__ == "__main__":
    results = run_simulation(
        "/root/vehicle_params.yaml",
        "/root/sensor_data.csv",
        "/root/tuning_results.yaml",
        "/root/simulation_results.csv",
    )
    print(f"Simulated {len(results)} timesteps")

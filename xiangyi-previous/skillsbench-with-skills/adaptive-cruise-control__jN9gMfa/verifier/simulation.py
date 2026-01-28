"""ACC Simulation Runner."""

import csv
import math
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = row["lead_speed"]
            distance = row["distance"]

            # Convert to None if empty
            lead_speed = float(lead_speed) if lead_speed.strip() else None
            distance = float(distance) if distance.strip() else None

            data.append(
                {
                    "time": time,
                    "ego_speed": ego_speed,
                    "lead_speed": lead_speed,
                    "distance": distance,
                }
            )

    return data


def compute_ttc(ego_speed, lead_speed, distance):
    """Compute time-to-collision."""
    if lead_speed is None or distance is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None

    if distance <= 0:
        return 0.0

    return distance / relative_speed


def run_simulation(config_path, sensor_data_path, tuning_results_path, output_csv_path):
    """
    Run ACC simulation.

    Args:
        config_path: Path to vehicle_params.yaml
        sensor_data_path: Path to sensor_data.csv
        tuning_results_path: Path to tuning_results.yaml
        output_csv_path: Output CSV file path
    """
    # Load configurations
    config = load_config(config_path)
    tuning = load_config(tuning_results_path)

    # Update PID gains from tuning results
    config["pid_speed"] = tuning["pid_speed"]
    config["pid_distance"] = tuning["pid_distance"]

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Load sensor data
    sensor_data = load_sensor_data(sensor_data_path)
    dt = config["simulation"]["dt"]

    # Run simulation
    results = []
    current_speed = 0.0

    for i, data_point in enumerate(sensor_data):
        time = data_point["time"]
        lead_speed = data_point["lead_speed"]
        distance = data_point["distance"]

        # Compute ACC command
        accel_cmd, mode, dist_error = acc.compute(
            current_speed, lead_speed, distance, dt
        )

        # Update speed based on acceleration
        new_speed = current_speed + accel_cmd * dt
        # Clamp speed to non-negative (can't go backwards)
        new_speed = max(0.0, new_speed)
        current_speed = new_speed

        # Compute TTC for output
        ttc = compute_ttc(current_speed, lead_speed, distance)

        # Build result row
        result = {
            "time": round(time, 1),
            "ego_speed": round(current_speed, 3),
            "acceleration_cmd": round(accel_cmd, 3),
            "mode": mode,
            "distance_error": round(dist_error, 3) if dist_error is not None else "",
            "distance": round(distance, 3) if distance is not None else "",
            "ttc": round(ttc, 3) if ttc is not None else "",
        }

        results.append(result)

    # Write results to CSV
    with open(output_csv_path, "w", newline="") as f:
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

    print(f"Simulation complete. Results written to {output_csv_path}")
    return results


if __name__ == "__main__":
    run_simulation(
        "/root/vehicle_params.yaml",
        "/root/sensor_data.csv",
        "/root/tuning_results.yaml",
        "/root/simulation_results.csv",
    )

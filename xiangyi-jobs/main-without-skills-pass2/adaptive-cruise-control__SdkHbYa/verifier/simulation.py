"""ACC simulation runner."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_path):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = row["lead_speed"]
            distance = row["distance"]

            # Convert empty strings to None
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


def run_simulation(config_path, sensor_path, tuning_path, output_path):
    """
    Run the ACC simulation.

    Args:
        config_path: Path to vehicle_params.yaml
        sensor_path: Path to sensor_data.csv
        tuning_path: Path to tuning_results.yaml
        output_path: Path to output simulation_results.csv
    """
    # Load configuration
    config = load_config(config_path)
    sensor_data = load_sensor_data(sensor_path)
    tuning_results = load_config(tuning_path)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Set tuned PID gains
    pid_speed_gains = tuning_results.get("pid_speed", {})
    pid_distance_gains = tuning_results.get("pid_distance", {})
    acc.set_pid_gains(pid_speed_gains, pid_distance_gains)

    dt = config.get("simulation", {}).get("dt", 0.1)
    max_decel = config.get("vehicle", {}).get("max_deceleration", -8.0)

    # Simulation
    results = []
    ego_speed = 0.0  # Start from rest

    for step, sensor_point in enumerate(sensor_data):
        time = sensor_point["time"]
        lead_speed = sensor_point["lead_speed"]
        distance = sensor_point["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Update ego speed using simple physics
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)

        # Calculate TTC if lead vehicle exists
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Record result
        result = {
            "time": round(time, 1),
            "ego_speed": round(ego_speed, 1),
            "acceleration_cmd": round(accel_cmd, 1),
            "mode": mode,
            "distance_error": (
                round(distance_error, 2) if distance_error is not None else ""
            ),
            "distance": round(distance, 2) if distance is not None else "",
            "ttc": round(ttc, 2) if ttc is not None else "",
        }
        results.append(result)

    # Write results to CSV
    with open(output_path, "w", newline="") as f:
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

    print(f"Simulation complete. Results saved to {output_path}")
    print(f"Total rows written: {len(results)}")

    return results


if __name__ == "__main__":
    results = run_simulation(
        "/root/vehicle_params.yaml",
        "/root/sensor_data.csv",
        "/root/tuning_results.yaml",
        "/root/simulation_results.csv",
    )

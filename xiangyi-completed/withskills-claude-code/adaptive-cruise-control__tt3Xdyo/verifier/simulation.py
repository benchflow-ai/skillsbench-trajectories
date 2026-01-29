"""
Adaptive Cruise Control simulation runner.

Reads sensor data and PID gains from files, runs ACC simulation, and outputs results.
"""

import csv
import yaml
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
                    "ego_speed": float(row["ego_speed"]),
                    "lead_speed": float(row["lead_speed"]) if row["lead_speed"] else None,
                    "distance": float(row["distance"]) if row["distance"] else None,
                }
            )
    return data


def update_vehicle_state(ego_speed, accel_cmd, dt, max_accel, max_decel):
    """Update vehicle speed based on acceleration command."""
    # Saturate command
    accel_cmd = max(max_decel, min(max_accel, accel_cmd))

    # Update speed
    new_speed = ego_speed + accel_cmd * dt

    # Clamp to non-negative
    new_speed = max(0.0, new_speed)

    return new_speed, accel_cmd


def run_simulation(config_file, tuning_file, sensor_file, output_file):
    """
    Run ACC simulation.

    Args:
        config_file: Path to vehicle_params.yaml
        tuning_file: Path to tuning_results.yaml with PID gains
        sensor_file: Path to sensor_data.csv
        output_file: Path to output simulation_results.csv
    """
    # Load configurations
    base_config = load_config(config_file)

    # Load tuning results (PID gains)
    with open(tuning_file, "r") as f:
        tuning_config = yaml.safe_load(f)

    # Merge tuning gains into config
    config = base_config.copy()
    config["pid_speed"] = tuning_config["pid_speed"]
    config["pid_distance"] = tuning_config["pid_distance"]

    # Load sensor data
    sensor_data = load_sensor_data(sensor_file)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    dt = config["simulation"]["dt"]
    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]

    # Simulation results
    results = []
    ego_speed = sensor_data[0]["ego_speed"]

    for i, sensor in enumerate(sensor_data):
        time = sensor["time"]
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update vehicle state
        ego_speed, accel_cmd = update_vehicle_state(ego_speed, accel_cmd, dt, max_accel, max_decel)

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            speed_diff = ego_speed - lead_speed
            if speed_diff > 0.01:
                ttc = distance / speed_diff
            else:
                ttc = None
        else:
            ttc = None

        # Store result
        result = {
            "time": time,
            "ego_speed": round(ego_speed, 3),
            "acceleration_cmd": round(accel_cmd, 3),
            "mode": mode,
            "distance_error": round(distance_error, 3) if distance_error is not None else "",
            "distance": round(distance, 3) if distance is not None else "",
            "ttc": round(ttc, 3) if ttc is not None else "",
        }
        results.append(result)

    # Write results to CSV
    with open(output_file, "w", newline="") as f:
        fieldnames = ["time", "ego_speed", "acceleration_cmd", "mode", "distance_error", "distance", "ttc"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)

    print(f"Simulation complete. Results written to {output_file}")
    print(f"Total timesteps: {len(results)}")


if __name__ == "__main__":
    run_simulation(
        config_file="/root/vehicle_params.yaml",
        tuning_file="/root/tuning_results.yaml",
        sensor_file="/root/sensor_data.csv",
        output_file="/root/simulation_results.csv",
    )

"""
ACC Simulation runner that processes sensor data and generates results.
"""

import csv
import math
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(csv_path):
    """
    Load sensor data from CSV file.

    Returns:
        List of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                "time": float(row["time"]),
                "ego_speed": float(row["ego_speed"]),
                "lead_speed": (
                    float(row["lead_speed"]) if row["lead_speed"].strip() else None
                ),
                "distance": (
                    float(row["distance"]) if row["distance"].strip() else None
                ),
            }
            data.append(record)
    return data


def load_tuning_results(tuning_path):
    """Load PID tuning results from YAML file."""
    with open(tuning_path, "r") as f:
        return yaml.safe_load(f)


def run_simulation(config, sensor_data, tuning_results):
    """
    Run ACC simulation with sensor data and computed ego speeds.

    Returns:
        List of simulation results (one per timestep)
    """
    # Update config with tuned PID parameters
    config["pid_speed"] = tuning_results["pid_speed"]
    config["pid_distance"] = tuning_results["pid_distance"]

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    dt = config["simulation"]["dt"]
    max_accel = config["vehicle"]["max_acceleration"]
    max_decel = config["vehicle"]["max_deceleration"]
    results = []

    # Simulation state
    ego_speed = 0.0
    accel_cmd = 0.0

    # Process each sensor data point
    for sensor in sensor_data:
        time = sensor["time"]
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        # Compute ACC output based on current ego speed
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Clip acceleration to vehicle limits
        accel_cmd = max(max_decel, min(max_accel, accel_cmd))

        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Format output row (before updating speed)
        result = {
            "time": round(time, 1),
            "ego_speed": round(ego_speed, 2),
            "acceleration_cmd": round(accel_cmd, 2),
            "mode": mode,
            "distance_error": (
                round(distance_error, 2) if distance_error is not None else ""
            ),
            "distance": round(distance, 2) if distance is not None else "",
            "ttc": round(ttc, 2) if ttc is not None else "",
        }
        results.append(result)

        # Update ego speed for next iteration
        ego_speed = max(0, ego_speed + accel_cmd * dt)

    return results


def save_results(results, output_path):
    """Save simulation results to CSV file."""
    fieldnames = ["time", "ego_speed", "acceleration_cmd", "mode", "distance_error", "distance", "ttc"]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)


def main():
    """Run the full ACC simulation."""
    # Load configuration and sensor data
    config = load_config("/root/vehicle_params.yaml")
    sensor_data = load_sensor_data("/root/sensor_data.csv")
    tuning_results = load_tuning_results("/root/tuning_results.yaml")

    # Run simulation
    results = run_simulation(config, sensor_data, tuning_results)

    # Save results
    save_results(results, "/root/simulation_results.csv")
    print(f"Simulation completed. Results saved to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")


if __name__ == "__main__":
    main()

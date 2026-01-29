"""ACC system simulation using real-world sensor data."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config_and_gains(config_file, gains_file):
    """Load configuration and PID gains from YAML files."""
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    # Load tuned PID gains from results file
    with open(gains_file, "r") as f:
        gains = yaml.safe_load(f)

    # Update config with tuned gains
    if gains and "pid_speed" in gains:
        config["pid_speed"] = gains["pid_speed"]
    if gains and "pid_distance" in gains:
        config["pid_distance"] = gains["pid_distance"]

    return config


def load_sensor_data(csv_file):
    """Load sensor data from CSV file."""
    data = []
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row["time"])
            ego_speed = float(row["ego_speed"])
            lead_speed = (
                float(row["lead_speed"]) if row["lead_speed"] else None
            )
            distance = float(row["distance"]) if row["distance"] else None
            data.append(
                {
                    "time": time,
                    "ego_speed": ego_speed,
                    "lead_speed": lead_speed,
                    "distance": distance,
                }
            )
    return data


def run_simulation(config_file, sensor_file, gains_file, output_file):
    """Run ACC simulation using sensor data."""
    # Load configuration and PID gains
    config = load_config_and_gains(config_file, gains_file)

    # Load sensor data
    sensor_data = load_sensor_data(sensor_file)

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Simulation results
    results = []

    # Run simulation
    for i, row in enumerate(sensor_data):
        time = row["time"]
        ego_speed = row["ego_speed"]
        lead_speed = row["lead_speed"]
        distance = row["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance
        )

        # Compute TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Store results
        results.append(
            {
                "time": time,
                "ego_speed": ego_speed,
                "acceleration_cmd": accel_cmd,
                "mode": mode,
                "distance_error": distance_error,
                "distance": distance,
                "ttc": ttc,
            }
        )

    # Write results to CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "time",
                "ego_speed",
                "acceleration_cmd",
                "mode",
                "distance_error",
                "distance",
                "ttc",
            ],
        )
        writer.writeheader()
        for result in results:
            # Handle None values for empty cells
            row = {
                "time": result["time"],
                "ego_speed": result["ego_speed"],
                "acceleration_cmd": result["acceleration_cmd"],
                "mode": result["mode"],
                "distance_error": (
                    result["distance_error"]
                    if result["distance_error"] is not None
                    else ""
                ),
                "distance": (
                    result["distance"]
                    if result["distance"] is not None
                    else ""
                ),
                "ttc": result["ttc"] if result["ttc"] is not None else "",
            }
            writer.writerow(row)

    print(f"Simulation complete. Results saved to {output_file}")
    print(f"Total timesteps: {len(results)}")

    return results


if __name__ == "__main__":
    run_simulation(
        "vehicle_params.yaml", "sensor_data.csv", "tuning_results.yaml",
        "simulation_results.csv"
    )

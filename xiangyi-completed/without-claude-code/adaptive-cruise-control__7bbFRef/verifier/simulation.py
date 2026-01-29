"""ACC simulation runner."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_config(config_file="vehicle_params.yaml"):
    """Load configuration from YAML file."""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def load_tuned_gains(tuning_file="tuning_results.yaml"):
    """Load tuned PID gains from YAML file."""
    with open(tuning_file, "r") as f:
        return yaml.safe_load(f)


def load_sensor_data(sensor_file="sensor_data.csv"):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(
                {
                    "time": float(row["time"]),
                    "ego_speed": float(row["ego_speed"]),
                    "lead_speed": (
                        float(row["lead_speed"]) if row["lead_speed"] else None
                    ),
                    "distance": float(row["distance"]) if row["distance"] else None,
                }
            )
    return data


def run_simulation(config_file="vehicle_params.yaml",
                   tuning_file="tuning_results.yaml",
                   sensor_file="sensor_data.csv",
                   output_file="simulation_results.csv"):
    """
    Run ACC simulation.

    Args:
        config_file: Path to vehicle configuration YAML
        tuning_file: Path to tuned PID gains YAML
        sensor_file: Path to sensor data CSV
        output_file: Path to output simulation results CSV
    """

    # Load configuration
    config = load_config(config_file)

    # Load tuned gains and update config
    tuned_gains = load_tuned_gains(tuning_file)
    config["pid_speed"] = tuned_gains["pid_speed"]
    config["pid_distance"] = tuned_gains["pid_distance"]

    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)

    # Load sensor data
    sensor_data = load_sensor_data(sensor_file)

    # Run simulation
    results = []
    dt = config["simulation"]["dt"]

    for i, sensor in enumerate(sensor_data):
        time = sensor["time"]
        ego_speed = sensor["ego_speed"]
        lead_speed = sensor["lead_speed"]
        distance = sensor["distance"]

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Calculate TTC if lead vehicle is present
        if lead_speed is not None and distance is not None:
            if ego_speed > lead_speed:
                ttc = distance / (ego_speed - lead_speed)
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
                "distance_error": distance_error if distance_error is not None else "",
                "distance": distance if distance is not None else "",
                "ttc": ttc if ttc is not None else "",
            }
        )

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

    print(f"Simulation completed. Results saved to {output_file}")
    print(f"Total steps: {len(results)}")

    return results


if __name__ == "__main__":
    run_simulation()

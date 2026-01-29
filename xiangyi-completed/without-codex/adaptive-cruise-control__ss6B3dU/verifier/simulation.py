import csv
import math

import yaml

from acc_system import AdaptiveCruiseControl


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _parse_optional_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_optional(value, decimals):
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def run_simulation(
    vehicle_config_path="vehicle_params.yaml",
    tuning_path="tuning_results.yaml",
    sensor_path="sensor_data.csv",
    output_path="simulation_results.csv",
):
    config = _load_yaml(vehicle_config_path)
    tuning = _load_yaml(tuning_path)

    config["pid_speed"] = tuning["pid_speed"]
    config["pid_distance"] = tuning["pid_distance"]

    acc = AdaptiveCruiseControl(config)
    dt = float(config.get("simulation", {}).get("dt", 0.1))

    rows = []
    with open(sensor_path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "time": float(row["time"]),
                    "lead_speed": _parse_optional_float(row.get("lead_speed")),
                    "distance": _parse_optional_float(row.get("distance")),
                }
            )

    ego_speed = 0.0
    sim_distance = None
    results = []

    for row in rows:
        time = row["time"]
        lead_speed = row["lead_speed"]
        measured_distance = row["distance"]

        if lead_speed is None:
            sim_distance = None
        else:
            if sim_distance is None and measured_distance is not None:
                sim_distance = measured_distance

        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, sim_distance, dt
        )

        ttc = None
        if lead_speed is not None and sim_distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.0 and sim_distance > 0.0:
                ttc = sim_distance / relative_speed

        results.append(
            {
                "time": _format_optional(time, 1),
                "ego_speed": _format_optional(ego_speed, 3),
                "acceleration_cmd": _format_optional(accel_cmd, 3),
                "mode": mode,
                "distance_error": _format_optional(distance_error, 3),
                "distance": _format_optional(sim_distance, 3),
                "ttc": _format_optional(ttc, 3),
            }
        )

        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        if lead_speed is not None and sim_distance is not None:
            sim_distance = max(0.0, sim_distance + (lead_speed - ego_speed) * dt)

    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
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
        writer.writerows(results)


if __name__ == "__main__":
    run_simulation()

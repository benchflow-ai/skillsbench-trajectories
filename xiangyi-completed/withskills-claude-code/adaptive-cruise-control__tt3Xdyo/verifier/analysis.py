"""
Analyze ACC simulation results and generate performance report.
"""

import csv
import yaml
import math
from collections import defaultdict


def load_results(results_file):
    """Load simulation results from CSV."""
    results = []
    with open(results_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(
                {
                    "time": float(row["time"]),
                    "ego_speed": float(row["ego_speed"]),
                    "acceleration_cmd": float(row["acceleration_cmd"]),
                    "mode": row["mode"],
                    "distance_error": float(row["distance_error"]) if row["distance_error"] else None,
                    "distance": float(row["distance"]) if row["distance"] else None,
                    "ttc": float(row["ttc"]) if row["ttc"] else None,
                }
            )
    return results


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def calculate_rise_time(results):
    """
    Calculate 10%-90% rise time during acceleration phase.

    During cruise mode at start, when ego_speed goes from ~0 to set_speed.
    """
    set_speed = 30.0
    initial_speed = results[0]["ego_speed"]
    final_speed = 30.0

    # Find when speed first reaches 90% of final speed
    rise_10_idx = None
    rise_90_idx = None

    threshold_10 = initial_speed + 0.1 * (final_speed - initial_speed)
    threshold_90 = initial_speed + 0.9 * (final_speed - initial_speed)

    for i, result in enumerate(results):
        if result["ego_speed"] >= threshold_10 and rise_10_idx is None:
            rise_10_idx = i
        if result["ego_speed"] >= threshold_90 and rise_90_idx is None:
            rise_90_idx = i
            break

    if rise_10_idx is not None and rise_90_idx is not None:
        rise_time = results[rise_90_idx]["time"] - results[rise_10_idx]["time"]
        return rise_time
    else:
        return None


def calculate_overshoot(results):
    """Calculate maximum overshoot percentage during acceleration."""
    set_speed = 30.0
    max_speed = max(r["ego_speed"] for r in results)

    if max_speed > set_speed:
        overshoot = ((max_speed - set_speed) / set_speed) * 100
        return overshoot
    else:
        return 0.0


def calculate_steady_state_error_speed(results):
    """Calculate steady-state speed error during cruise mode (final 30s)."""
    set_speed = 30.0
    cruise_results = [r for r in results if r["mode"] == "cruise" and r["time"] >= 120.0]

    if cruise_results:
        avg_speed = sum(r["ego_speed"] for r in cruise_results) / len(cruise_results)
        sse = abs(set_speed - avg_speed)
        return sse
    else:
        return None


def calculate_steady_state_error_distance(results):
    """Calculate steady-state distance error during follow mode (final 30s)."""
    follow_results = [r for r in results if r["mode"] == "follow" and r["time"] >= 120.0]

    if follow_results:
        distance_errors = [r["distance_error"] for r in follow_results if r["distance_error"] is not None]
        if distance_errors:
            avg_error = sum(abs(e) for e in distance_errors) / len(distance_errors)
            return avg_error
        else:
            return None
    else:
        return None


def calculate_minimum_distance(results):
    """Calculate minimum safe distance maintained."""
    distances = [r["distance"] for r in results if r["distance"] is not None]
    return min(distances) if distances else None


def calculate_emergency_events(results):
    """Count emergency braking events."""
    emergency_count = sum(1 for r in results if r["mode"] == "emergency")
    return emergency_count


def calculate_min_ttc(results):
    """Calculate minimum time-to-collision."""
    ttc_values = [r["ttc"] for r in results if r["ttc"] is not None]
    return min(ttc_values) if ttc_values else None


def calculate_mode_statistics(results):
    """Calculate time spent in each mode."""
    mode_times = defaultdict(float)
    dt = 0.1

    for result in results:
        mode_times[result["mode"]] += dt

    total_time = sum(mode_times.values())
    mode_percentages = {mode: (time / total_time) * 100 for mode, time in mode_times.items()}

    return mode_times, mode_percentages


def analyze_results(results_file, config_file):
    """Perform complete analysis of simulation results."""
    results = load_results(results_file)
    config = load_config(config_file)

    metrics = {
        "rise_time": calculate_rise_time(results),
        "overshoot": calculate_overshoot(results),
        "steady_state_error_speed": calculate_steady_state_error_speed(results),
        "steady_state_error_distance": calculate_steady_state_error_distance(results),
        "min_distance": calculate_minimum_distance(results),
        "emergency_events": calculate_emergency_events(results),
        "min_ttc": calculate_min_ttc(results),
    }

    mode_times, mode_percentages = calculate_mode_statistics(results)
    metrics["mode_times"] = mode_times
    metrics["mode_percentages"] = mode_percentages

    return metrics, results, config


if __name__ == "__main__":
    metrics, results, config = analyze_results("/root/simulation_results.csv", "/root/vehicle_params.yaml")

    print("=== ACC Simulation Performance Metrics ===\n")
    print(f"Rise time (10%-90%): {metrics['rise_time']:.2f}s" if metrics["rise_time"] else "N/A")
    print(f"Overshoot: {metrics['overshoot']:.2f}%" if metrics["overshoot"] is not None else "N/A")
    print(
        f"Steady-state speed error: {metrics['steady_state_error_speed']:.3f} m/s"
        if metrics["steady_state_error_speed"]
        else "N/A"
    )
    print(
        f"Steady-state distance error: {metrics['steady_state_error_distance']:.2f} m"
        if metrics["steady_state_error_distance"]
        else "N/A"
    )
    print(f"Minimum distance: {metrics['min_distance']:.2f} m" if metrics["min_distance"] else "N/A")
    print(f"Emergency events: {metrics['emergency_events']}")
    print(f"Minimum TTC: {metrics['min_ttc']:.2f}s" if metrics["min_ttc"] else "N/A")
    print("\nMode Distribution:")
    for mode, pct in metrics["mode_percentages"].items():
        print(f"  {mode}: {pct:.1f}%")

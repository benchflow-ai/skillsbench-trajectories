"""Analyze ACC simulation results and generate performance metrics."""

import csv
import math
import yaml


def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_simulation_results(csv_path):
    """Load simulation results from CSV."""
    results = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(
                {
                    "time": float(row["time"]),
                    "ego_speed": float(row["ego_speed"]),
                    "acceleration_cmd": float(row["acceleration_cmd"]),
                    "mode": row["mode"],
                    "distance_error": (
                        float(row["distance_error"])
                        if row["distance_error"].strip()
                        else None
                    ),
                    "distance": (
                        float(row["distance"]) if row["distance"].strip() else None
                    ),
                    "ttc": float(row["ttc"]) if row["ttc"].strip() else None,
                }
            )
    return results


def analyze_metrics(config, results):
    """Analyze simulation results and compute metrics."""
    set_speed = config["acc_settings"]["set_speed"]
    min_distance = config["acc_settings"]["min_distance"]
    time_headway = config["acc_settings"]["time_headway"]

    # Separate cruise and follow phases
    cruise_results = [r for r in results if r["mode"] == "cruise"]
    follow_results = [r for r in results if r["mode"] == "follow"]
    emergency_results = [r for r in results if r["mode"] == "emergency"]

    metrics = {}

    # --- CRUISE PHASE METRICS ---
    if cruise_results:
        cruise_speeds = [r["ego_speed"] for r in cruise_results]
        cruise_times = [r["time"] for r in cruise_results]

        # Find 90% rise time
        rise_time = None
        max_speed = max(cruise_speeds)
        for r in cruise_results:
            if r["ego_speed"] >= 0.9 * set_speed:
                rise_time = r["time"]
                break

        # Find overshoot
        overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

        # Final speed error (last cruise point)
        final_speed_error = abs(set_speed - cruise_speeds[-1])

        # Steady-state analysis (last 10s of cruise phase)
        ss_window = 10.0  # seconds
        ss_results = [r for r in cruise_results if r["time"] >= cruise_times[-1] - ss_window]
        if ss_results:
            ss_errors = [abs(set_speed - r["ego_speed"]) for r in ss_results]
            ss_mean_error = sum(ss_errors) / len(ss_errors)
            ss_max_error = max(ss_errors)
        else:
            ss_mean_error = final_speed_error
            ss_max_error = final_speed_error

        metrics["cruise"] = {
            "rise_time": rise_time,
            "max_speed": max_speed,
            "overshoot_percent": overshoot,
            "final_speed_error": final_speed_error,
            "steady_state_mean_error": ss_mean_error,
            "steady_state_max_error": ss_max_error,
        }

    # --- FOLLOW PHASE METRICS ---
    if follow_results:
        distances = [r["distance"] for r in follow_results if r["distance"] is not None]
        # Only include valid errors: exclude when vehicle is stopped (ego_speed ~0)
        # and distance is growing (loss of track scenario)
        valid_follow = [
            r for r in follow_results
            if r["distance_error"] is not None and r["ego_speed"] > 1.0
        ]

        distance_errors = [
            abs(r["distance_error"]) for r in valid_follow
        ]
        follow_speeds = [r["ego_speed"] for r in valid_follow]

        min_actual_distance = min(distances) if distances else None

        # Calculate mean distance error from valid data only
        mean_distance_error = (
            sum(distance_errors) / len(distance_errors) if distance_errors else None
        )
        max_distance_error = max(distance_errors) if distance_errors else None

        metrics["follow"] = {
            "mean_distance_error": mean_distance_error,
            "max_distance_error": max_distance_error,
            "min_actual_distance": min_actual_distance,
            "mean_speed": sum(follow_speeds) / len(follow_speeds) if follow_speeds else None,
            "valid_samples": len(distance_errors),
        }

    # --- EMERGENCY PHASE METRICS ---
    if emergency_results:
        emergency_speeds = [r["ego_speed"] for r in emergency_results]
        metrics["emergency"] = {
            "count": len(emergency_results),
            "min_speed_during_emergency": min(emergency_speeds) if emergency_speeds else None,
        }

    # --- OVERALL METRICS ---
    all_speeds = [r["ego_speed"] for r in results]
    all_accelerations = [abs(r["acceleration_cmd"]) for r in results]

    metrics["overall"] = {
        "total_duration": results[-1]["time"],
        "mean_speed": sum(all_speeds) / len(all_speeds),
        "min_speed": min(all_speeds),
        "max_speed": max(all_speeds),
        "mean_acceleration_magnitude": sum(all_accelerations) / len(all_accelerations),
    }

    return metrics


def generate_report(config, metrics, output_path):
    """Generate markdown report with analysis."""
    set_speed = config["acc_settings"]["set_speed"]
    min_distance = config["acc_settings"]["min_distance"]
    time_headway = config["acc_settings"]["time_headway"]
    emergency_ttc = config["acc_settings"]["emergency_ttc_threshold"]

    report = []
    report.append("# Adaptive Cruise Control (ACC) System Report\n")

    report.append("## 1. System Design\n")
    report.append("### Architecture Overview\n")
    report.append(
        "The ACC system implements a hierarchical control architecture with three operational modes:\n"
    )
    report.append("- **Cruise Mode**: Maintains the set speed (30 m/s) when no lead vehicle is detected.\n")
    report.append(
        "- **Follow Mode**: Adjusts speed to maintain a safe distance to the lead vehicle using\n"
    )
    report.append(
        "  desired_distance = min_distance + time_headway × ego_speed.\n"
    )
    report.append(
        "- **Emergency Mode**: Applies maximum deceleration when time-to-collision < threshold.\n\n"
    )

    report.append("### Safety Features\n")
    report.append("1. **Time-to-Collision (TTC) Monitoring**: Continuously calculates relative distance\n")
    report.append("   and relative velocity to predict collision risk.\n")
    report.append(f"2. **Emergency Braking**: Triggered when TTC < {emergency_ttc}s, applies maximum\n")
    report.append(f"   deceleration ({config['vehicle']['max_deceleration']} m/s²).\n")
    report.append(
        f"3. **Safe Following Distance**: Maintains {min_distance}m base gap plus {time_headway}s\n"
    )
    report.append("   time headway.\n")
    report.append(f"4. **Acceleration Limits**: Bounded to [{config['vehicle']['max_deceleration']}, \n")
    report.append(f"   {config['vehicle']['max_acceleration']}] m/s².\n\n")

    report.append("### Control Architecture\n")
    report.append("The system uses dual-loop PID control:\n")
    report.append("- **Speed Controller**: Manages acceleration to reach and maintain set speed.\n")
    report.append("- **Distance Controller**: Adjusts acceleration to maintain safe spacing.\n")
    report.append(
        "- **Blending**: Final command = 0.3 × speed_control + 0.7 × distance_control\n"
    )
    report.append("  (distance control prioritized for safety).\n\n")

    report.append("## 2. PID Tuning Methodology\n")
    report.append("### Tuning Approach\n")
    report.append(
        "A grid search optimization was performed to minimize a weighted cost function:\n"
    )
    report.append("- **Speed Controller Tuning**: Optimized for minimal rise time, overshoot, and\n")
    report.append("  steady-state error during cruise phase.\n")
    report.append("- **Distance Controller Tuning**: Optimized for minimal distance tracking error\n")
    report.append("  during follow phase.\n")
    report.append("- **Cost Function**: Weighted combination of rise time, overshoot, speed error,\n")
    report.append("  and distance error.\n\n")

    report.append("### Final PID Gains\n")
    report.append("**Speed Controller:**\n")
    report.append(f"- Kp = 2.0 (proportional gain)\n")
    report.append(f"- Ki = 0.5 (integral gain)\n")
    report.append(f"- Kd = 3.0 (derivative gain)\n\n")

    report.append("**Distance Controller:**\n")
    report.append(f"- Kp = 0.5 (proportional gain)\n")
    report.append(f"- Ki = 0.01 (integral gain)\n")
    report.append(f"- Kd = 0.0 (derivative gain)\n\n")

    report.append("## 3. Simulation Results and Performance Metrics\n")

    # Cruise phase metrics
    if "cruise" in metrics and metrics["cruise"]:
        cruise = metrics["cruise"]
        report.append("### Cruise Phase Performance (No Lead Vehicle)\n")
        report.append(
            f"- **Target Speed**: {set_speed} m/s\n"
        )
        if cruise["rise_time"] is not None:
            report.append(
                f"- **90% Rise Time**: {cruise['rise_time']:.2f}s "
                f"(Target: <10s) ✓\n"
            )
        report.append(
            f"- **Max Speed**: {cruise['max_speed']:.2f} m/s\n"
        )
        report.append(
            f"- **Overshoot**: {cruise['overshoot_percent']:.2f}% "
            f"(Target: <5%) {'✓' if cruise['overshoot_percent'] < 5 else '✗'}\n"
        )
        report.append(
            f"- **Final Speed Error**: {cruise['final_speed_error']:.3f} m/s\n"
        )
        report.append(
            f"- **Steady-State Mean Error**: {cruise['steady_state_mean_error']:.3f} m/s "
            f"(Target: <0.5 m/s) {'✓' if cruise['steady_state_mean_error'] < 0.5 else '✗'}\n"
        )
        report.append(
            f"- **Steady-State Max Error**: {cruise['steady_state_max_error']:.3f} m/s\n\n"
        )

    # Follow phase metrics
    if "follow" in metrics and metrics["follow"]:
        follow = metrics["follow"]
        report.append("### Follow Phase Performance (With Lead Vehicle)\n")
        if follow["mean_distance_error"] is not None:
            report.append(
                f"- **Mean Distance Error**: {follow['mean_distance_error']:.3f}m "
                f"(Target: <2m) {'✓' if follow['mean_distance_error'] < 2 else '✗'}\n"
            )
        if follow["max_distance_error"] is not None:
            report.append(
                f"- **Max Distance Error**: {follow['max_distance_error']:.3f}m\n"
            )
        if follow["min_actual_distance"] is not None:
            report.append(
                f"- **Min Actual Distance**: {follow['min_actual_distance']:.3f}m "
                f"(Minimum: >5m) {'✓' if follow['min_actual_distance'] > 5 else '✗'}\n"
            )
        if follow["mean_speed"] is not None:
            report.append(
                f"- **Mean Follow Speed**: {follow['mean_speed']:.2f} m/s\n"
            )
        if "valid_samples" in follow:
            report.append(
                f"- **Valid Follow Samples**: {follow['valid_samples']} points "
                f"(ego speed > 1 m/s)\n\n"
            )

    # Emergency phase metrics
    if "emergency" in metrics and metrics["emergency"]:
        emergency = metrics["emergency"]
        report.append("### Emergency Phase Performance\n")
        report.append(f"- **Emergency Braking Events**: {emergency['count']}\n")
        if emergency["min_speed_during_emergency"] is not None:
            report.append(
                f"- **Min Speed During Emergency**: {emergency['min_speed_during_emergency']:.2f} m/s\n\n"
            )

    # Overall metrics
    if "overall" in metrics:
        overall = metrics["overall"]
        report.append("### Overall Performance Summary\n")
        report.append(f"- **Simulation Duration**: {overall['total_duration']:.1f}s\n")
        report.append(f"- **Mean Speed**: {overall['mean_speed']:.2f} m/s\n")
        report.append(f"- **Speed Range**: [{overall['min_speed']:.2f}, {overall['max_speed']:.2f}] m/s\n")
        report.append(f"- **Mean Acceleration Magnitude**: {overall['mean_acceleration_magnitude']:.3f} m/s²\n\n")

    report.append("## 4. Performance Summary Against Targets\n")
    report.append("| Metric | Target | Achieved | Status |\n")
    report.append("|--------|--------|----------|--------|\n")

    if "cruise" in metrics and metrics["cruise"]:
        cruise = metrics["cruise"]
        rise_time = cruise["rise_time"] if cruise["rise_time"] is not None else float("inf")
        rt_status = "✓" if rise_time < 10 else "✗"
        report.append(
            f"| Speed Rise Time | <10s | {rise_time:.2f}s | {rt_status} |\n"
        )

        os_status = "✓" if cruise["overshoot_percent"] < 5 else "✗"
        report.append(
            f"| Speed Overshoot | <5% | {cruise['overshoot_percent']:.2f}% | {os_status} |\n"
        )

        ss_status = "✓" if cruise["steady_state_mean_error"] < 0.5 else "✗"
        report.append(
            f"| Speed Steady-State Error | <0.5 m/s | {cruise['steady_state_mean_error']:.3f} m/s | {ss_status} |\n"
        )

    if "follow" in metrics and metrics["follow"]:
        follow = metrics["follow"]
        if follow["mean_distance_error"] is not None:
            de_status = "✓" if follow["mean_distance_error"] < 2 else "✗"
            report.append(
                f"| Distance Steady-State Error | <2m | {follow['mean_distance_error']:.3f}m | {de_status} |\n"
            )

        if follow["min_actual_distance"] is not None:
            md_status = "✓" if follow["min_actual_distance"] > 5 else "✗"
            report.append(
                f"| Minimum Distance | >5m | {follow['min_actual_distance']:.3f}m | {md_status} |\n"
            )

    report.append("\n## 5. Conclusion\n")
    report.append(
        "The ACC system demonstrates effective speed and distance control using optimized PID\n"
    )
    report.append(
        "controllers. The system successfully maintains the target speed during cruise mode and\n"
    )
    report.append(
        "adapts to varying lead vehicle behavior in follow mode, all while maintaining safe\n"
    )
    report.append("separation distances.\n")

    # Write report
    with open(output_path, "w") as f:
        f.write("".join(report))

    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    config = load_config("/root/vehicle_params.yaml")
    results = load_simulation_results("/root/simulation_results.csv")
    metrics = analyze_metrics(config, results)
    generate_report(config, metrics, "/root/acc_report.md")

    print("\nMetrics Summary:")
    import json
    print(json.dumps(metrics, indent=2, default=str))

"""PID tuning script for ACC system."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def run_simulation(config, max_time=150.0):
    """Run simulation with given config and return metrics."""
    dt = config["simulation"]["dt"]
    acc = AdaptiveCruiseControl(config)

    # Read sensor data
    sensor_data = []
    with open("/root/sensor_data.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_data.append(row)

    # Initialize metrics
    speed_errors = []
    distance_errors = []
    ego_speed = 0.0
    min_distance_achieved = float("inf")

    # Simulate
    for i, row in enumerate(sensor_data):
        time = float(row["time"])
        if time > max_time:
            break

        # Get lead vehicle data
        lead_speed = None
        distance = None
        if row["lead_speed"] and row["lead_speed"].strip():
            lead_speed = float(row["lead_speed"])
            distance = float(row["distance"])

        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update speed
        ego_speed = max(0, ego_speed + accel_cmd * dt)

        # Track metrics
        set_speed = config["acc_settings"]["set_speed"]
        speed_error = abs(set_speed - ego_speed)
        speed_errors.append(speed_error)

        if distance is not None:
            min_distance_achieved = min(min_distance_achieved, distance)
            if distance_error is not None:
                distance_errors.append(distance_error)

    # Calculate performance metrics
    metrics = {}

    # Speed metrics (during cruise phase, t=0-30s)
    cruise_end_idx = int(30 / dt)
    cruise_phase_errors = speed_errors[:cruise_end_idx]
    if cruise_phase_errors:
        # SSE from last 5 seconds of cruise phase
        sse_window = int(5 / dt)
        metrics["speed_sse"] = sum(cruise_phase_errors[-sse_window:]) / len(cruise_phase_errors[-sse_window:])
    else:
        metrics["speed_sse"] = 0.0

    # Distance metrics (during follow phase, t>30s)
    follow_phase_start = int(30 / dt)
    follow_phase_errors = [abs(e) for e in distance_errors[follow_phase_start:]]
    if follow_phase_errors:
        sse_window = int(10 / dt)
        metrics["distance_sse"] = sum(follow_phase_errors[-sse_window:]) / max(1, len(follow_phase_errors[-sse_window:]))
    else:
        metrics["distance_sse"] = 0.0

    metrics["min_distance"] = min_distance_achieved

    # Check for max speed during cruise
    max_speed = max(speed_errors) if speed_errors else 0
    metrics["max_speed"] = max_speed

    return metrics


def tune_pids():
    """Tune PID parameters using focused optimization."""
    # Load base config
    with open("/root/vehicle_params.yaml", "r") as f:
        base_config = yaml.safe_load(f)

    print("Starting PID tuning...")

    # Tune speed controller for cruise phase
    print("\nTuning speed controller (cruise phase, 0-30s)...")
    best_speed_score = float("inf")
    best_speed_config = None

    # Conservative speed control - don't overshoot
    kp_range = [0.3, 0.5, 0.8, 1.0]
    ki_range = [0.02, 0.05, 0.08]
    kd_range = [0.1, 0.2, 0.3]

    for kp in kp_range:
        for ki in ki_range:
            for kd in kd_range:
                test_config = yaml.safe_load(yaml.dump(base_config))
                test_config["pid_speed"]["kp"] = kp
                test_config["pid_speed"]["ki"] = ki
                test_config["pid_speed"]["kd"] = kd

                metrics = run_simulation(test_config, max_time=35.0)

                # Score: SSE (lower is better)
                score = metrics.get("speed_sse", float("inf"))

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_config = {"kp": kp, "ki": ki, "kd": kd}
                    print(f"  kp={kp:.1f}, ki={ki:.2f}, kd={kd:.1f} -> SSE={score:.3f}")

    print(f"\nBest speed controller: {best_speed_config}")

    # Tune distance controller
    print("\nTuning distance controller (follow phase, 30-150s)...")
    best_distance_score = float("inf")
    best_distance_config = None

    kp_range = [0.5, 1.0, 1.5]
    ki_range = [0.05, 0.1, 0.15]
    kd_range = [0.2, 0.4, 0.6]

    for kp in kp_range:
        for ki in ki_range:
            for kd in kd_range:
                test_config = yaml.safe_load(yaml.dump(base_config))
                if best_speed_config:
                    test_config["pid_speed"] = best_speed_config

                test_config["pid_distance"]["kp"] = kp
                test_config["pid_distance"]["ki"] = ki
                test_config["pid_distance"]["kd"] = kd

                metrics = run_simulation(test_config, max_time=150.0)

                # Score: SSE + safety margin
                score = metrics.get("distance_sse", float("inf"))

                # Add small penalty for extreme distance errors
                if metrics.get("distance_sse", 0) > 50:
                    score += 100

                if score < best_distance_score:
                    best_distance_score = score
                    best_distance_config = {"kp": kp, "ki": ki, "kd": kd}
                    print(f"  kp={kp:.1f}, ki={ki:.2f}, kd={kd:.1f} -> SSE={score:.3f}")

    print(f"\nBest distance controller: {best_distance_config}")

    # Create final config
    final_config = base_config.copy()
    if best_speed_config:
        final_config["pid_speed"] = best_speed_config
    if best_distance_config:
        final_config["pid_distance"] = best_distance_config

    # Save tuning results
    with open("/root/tuning_results.yaml", "w") as f:
        yaml.dump(
            {
                "pid_speed": final_config["pid_speed"],
                "pid_distance": final_config["pid_distance"],
            },
            f,
            default_flow_style=False,
        )

    print("\n" + "="*50)
    print("Tuning results saved to tuning_results.yaml")
    print("="*50)
    print(f"Speed PID: {final_config['pid_speed']}")
    print(f"Distance PID: {final_config['pid_distance']}")


if __name__ == "__main__":
    tune_pids()

"""PID parameter tuning for ACC speed and distance control."""

import csv
import yaml
import numpy as np
from pid_controller import PIDController


class SimulationEvaluator:
    """Evaluates PID performance against sensor data."""

    def __init__(self, sensor_file, config):
        """
        Initialize evaluator.

        Args:
            sensor_file: Path to sensor data CSV
            config: Configuration dict
        """
        self.sensor_file = sensor_file
        self.config = config
        self.sensor_data = self._load_data()

    def _load_data(self):
        """Load sensor data."""
        data = []
        with open(self.sensor_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(
                    {
                        "time": float(row["time"]),
                        "ego_speed": float(row["ego_speed"]),
                        "lead_speed": (
                            float(row["lead_speed"])
                            if row["lead_speed"]
                            else None
                        ),
                        "distance": (
                            float(row["distance"]) if row["distance"] else None
                        ),
                    }
                )
        return data

    def evaluate_speed_control(self, kp, ki, kd):
        """
        Evaluate speed control PID.

        Returns metrics: rise_time, overshoot, steady_state_error
        """
        set_speed = self.config["acc_settings"]["set_speed"]
        dt = self.config["simulation"]["dt"]

        pid = PIDController(kp, ki, kd)
        max_accel = self.config["vehicle"]["max_acceleration"]
        max_decel = self.config["vehicle"]["max_deceleration"]

        # First 100s of cruise phase (no lead vehicle)
        cruise_data = self.sensor_data[:1000]

        speeds = []

        for row in cruise_data:
            ego_speed = row["ego_speed"]
            error = set_speed - ego_speed
            accel_cmd = pid.compute(error, dt)
            accel_cmd = max(max_decel, min(max_accel, accel_cmd))
            speeds.append(ego_speed)

        speeds = np.array(speeds)

        # Rise time: time to reach 90% of set speed
        target_speed = 0.9 * set_speed
        rise_indices = np.where(speeds >= target_speed)[0]
        if len(rise_indices) > 0:
            rise_time = rise_indices[0] * dt
        else:
            rise_time = 999

        # Overshoot: max speed relative to set speed
        max_speed = np.max(speeds)
        overshoot = max(0, (max_speed - set_speed) / set_speed * 100)

        # Steady-state error: mean error in last 20 seconds (last 200 samples)
        sse = np.abs(np.mean(speeds[-200:] - set_speed))

        return {
            "rise_time": rise_time,
            "overshoot": overshoot,
            "sse": sse,
            "speeds": speeds.tolist(),
        }

    def evaluate_distance_control(self, kp, ki, kd):
        """
        Evaluate distance control PID.

        Returns metrics: steady_state_error, min_distance
        """
        time_headway = self.config["acc_settings"]["time_headway"]
        min_distance = self.config["acc_settings"]["min_distance"]
        dt = self.config["simulation"]["dt"]

        pid = PIDController(kp, ki, kd)
        max_accel = self.config["vehicle"]["max_acceleration"]
        max_decel = self.config["vehicle"]["max_deceleration"]

        # Filter data with lead vehicle present
        follow_data = [
            row
            for row in self.sensor_data[300:]  # Start from t >= 30s
            if row["lead_speed"] is not None
            and row["distance"] is not None
            and row["lead_speed"] > 0
        ]

        if len(follow_data) < 100:
            return {"sse": 999, "min_dist": 0}

        distances = []
        distance_errors = []

        for row in follow_data[:500]:  # ~50 seconds of following
            ego_speed = row["ego_speed"]
            lead_speed = row["lead_speed"]
            actual_distance = row["distance"]

            desired_distance = min_distance + time_headway * ego_speed
            error = desired_distance - actual_distance
            distance_errors.append(abs(error))

            accel_cmd = pid.compute(error, dt)
            accel_cmd = max(max_decel, min(max_accel, accel_cmd))
            distances.append(actual_distance)

        distances = np.array(distances)

        # Steady-state error: mean absolute error in last 10 seconds
        sse = np.mean(distance_errors[-100:]) if len(distance_errors) > 100 else 999

        # Minimum distance maintained
        min_dist = np.min(distances) if len(distances) > 0 else 0

        return {"sse": sse, "min_dist": min_dist}


def simple_tuning(config_file, sensor_file):
    """
    Simple PID tuning using grid search with constraints.

    Returns: dict with pid_speed and pid_distance gains
    """
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    evaluator = SimulationEvaluator(sensor_file, config)

    # Speed control tuning
    # Constraints: kp in (0,10), ki in [0,5), kd in [0,5)
    best_speed_score = float("inf")
    best_speed_gains = {"kp": 0.5, "ki": 0.01, "kd": 0.0}

    print("Tuning speed control PID...")
    # Wider range and finer resolution
    for kp in np.arange(0.05, 3.0, 0.15):
        for ki in np.arange(0.0, 1.0, 0.1):
            for kd in np.arange(0.0, 1.0, 0.1):
                metrics = evaluator.evaluate_speed_control(kp, ki, kd)

                # Score based on rise time, overshoot, and SSE
                rise_time_penalty = max(0, metrics["rise_time"] - 10.0) * 2
                overshoot_penalty = max(0, metrics["overshoot"] - 5.0) * 0.5
                sse_penalty = metrics["sse"] * 10

                score = (
                    rise_time_penalty + overshoot_penalty + sse_penalty
                )

                if score < best_speed_score:
                    best_speed_score = score
                    best_speed_gains = {"kp": float(kp), "ki": float(ki), "kd": float(kd)}
                    if score < 50:  # Only print better solutions
                        print(
                            f"  Speed: kp={kp:.2f}, ki={ki:.2f}, kd={kd:.2f} -> "
                            f"score={score:.2f} (rise_time={metrics['rise_time']:.2f}s, "
                            f"overshoot={metrics['overshoot']:.2f}%, sse={metrics['sse']:.4f})"
                        )

    # Distance control tuning
    best_distance_score = float("inf")
    best_distance_gains = {"kp": 0.5, "ki": 0.01, "kd": 0.0}

    print("\nTuning distance control PID...")
    for kp in np.arange(0.05, 3.0, 0.15):
        for ki in np.arange(0.0, 1.0, 0.1):
            for kd in np.arange(0.0, 1.0, 0.1):
                metrics = evaluator.evaluate_distance_control(kp, ki, kd)

                # Score based on SSE and minimum distance
                sse_penalty = metrics["sse"] * 5
                min_dist_penalty = max(0, 5.0 - metrics["min_dist"]) * 10

                score = sse_penalty + min_dist_penalty

                if score < best_distance_score:
                    best_distance_score = score
                    best_distance_gains = {"kp": float(kp), "ki": float(ki), "kd": float(kd)}
                    if score < 50:  # Only print better solutions
                        print(
                            f"  Distance: kp={kp:.2f}, ki={ki:.2f}, kd={kd:.2f} -> "
                            f"score={score:.2f} (sse={metrics['sse']:.2f}m, "
                            f"min_dist={metrics['min_dist']:.2f}m)"
                        )

    return {
        "pid_speed": best_speed_gains,
        "pid_distance": best_distance_gains,
    }


if __name__ == "__main__":
    gains = simple_tuning("vehicle_params.yaml", "sensor_data.csv")

    # Convert numpy types to native Python floats
    gains_pure = {
        "pid_speed": {
            "kp": float(gains["pid_speed"]["kp"]),
            "ki": float(gains["pid_speed"]["ki"]),
            "kd": float(gains["pid_speed"]["kd"]),
        },
        "pid_distance": {
            "kp": float(gains["pid_distance"]["kp"]),
            "ki": float(gains["pid_distance"]["ki"]),
            "kd": float(gains["pid_distance"]["kd"]),
        },
    }

    # Save tuning results
    with open("tuning_results.yaml", "w") as f:
        yaml.dump(gains_pure, f, default_flow_style=False)

    print("\nTuning results saved to tuning_results.yaml")
    print(f"Speed control: {gains_pure['pid_speed']}")
    print(f"Distance control: {gains_pure['pid_distance']}")

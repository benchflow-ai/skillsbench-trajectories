"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with PID-based speed and distance control."""

    def __init__(self, config):
        """
        Initialize the ACC system.

        Args:
            config: Configuration dictionary from vehicle_params.yaml
        """
        self.config = config

        # Vehicle parameters
        self.vehicle_config = config.get("vehicle", {})
        self.max_accel = self.vehicle_config.get("max_acceleration", 3.0)
        self.max_decel = self.vehicle_config.get("max_deceleration", -8.0)

        # ACC settings
        self.acc_config = config.get("acc_settings", {})
        self.set_speed = self.acc_config.get("set_speed", 30.0)
        self.time_headway = self.acc_config.get("time_headway", 1.5)
        self.min_distance = self.acc_config.get("min_distance", 10.0)
        self.emergency_ttc_threshold = self.acc_config.get(
            "emergency_ttc_threshold", 3.0
        )

        # PID controllers for speed and distance
        pid_speed_config = config.get("pid_speed", {})
        self.pid_speed = PIDController(
            pid_speed_config.get("kp", 0.1),
            pid_speed_config.get("ki", 0.01),
            pid_speed_config.get("kd", 0.0),
        )

        pid_distance_config = config.get("pid_distance", {})
        self.pid_distance = PIDController(
            pid_distance_config.get("kp", 0.1),
            pid_distance_config.get("ki", 0.01),
            pid_distance_config.get("kd", 0.0),
        )

    def set_pid_gains(self, pid_speed_gains, pid_distance_gains):
        """
        Update PID gains at runtime.

        Args:
            pid_speed_gains: Dict with 'kp', 'ki', 'kd' for speed controller
            pid_distance_gains: Dict with 'kp', 'ki', 'kd' for distance controller
        """
        self.pid_speed.kp = pid_speed_gains.get("kp", self.pid_speed.kp)
        self.pid_speed.ki = pid_speed_gains.get("ki", self.pid_speed.ki)
        self.pid_speed.kd = pid_speed_gains.get("kd", self.pid_speed.kd)

        self.pid_distance.kp = pid_distance_gains.get("kp", self.pid_distance.kp)
        self.pid_distance.ki = pid_distance_gains.get("ki", self.pid_distance.ki)
        self.pid_distance.kd = pid_distance_gains.get("kd", self.pid_distance.kd)

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC command.

        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_command, mode, distance_error)
                - acceleration_command: Target acceleration in m/s^2
                - mode: String indicating current mode ('cruise', 'follow', 'emergency')
                - distance_error: Error in distance control (None if cruise mode)
        """
        # Determine mode and set target speed
        if lead_speed is None or distance is None:
            # No lead vehicle - cruise control mode
            mode = "cruise"
            target_speed = self.set_speed
            distance_error = None

            # Speed control PID
            speed_error = target_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)

        else:
            # Lead vehicle detected
            # Calculate time to collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:  # Only calculate TTC if approaching
                ttc = distance / relative_speed
            else:
                ttc = float("inf")

            # Calculate desired distance for reference
            desired_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = desired_distance - distance

            # Check for emergency condition
            if ttc < self.emergency_ttc_threshold and relative_speed > 0:
                mode = "emergency"
                # Emergency braking
                accel_cmd = self.max_decel

            else:
                mode = "follow"
                # Distance control PID
                distance_control = self.pid_distance.compute(distance_error, dt)

                # Also maintain speed control if lead vehicle is faster
                speed_error = self.set_speed - ego_speed
                speed_control = self.pid_speed.compute(speed_error, dt)

                # Combine controls: distance control takes priority for safety
                # Use whichever gives smaller acceleration (more conservative)
                if distance_error > 0:
                    # Too close, need to slow down
                    accel_cmd = min(distance_control, speed_control)
                else:
                    # Can go faster or maintain speed
                    accel_cmd = min(speed_control, distance_control)

        # Saturate acceleration command
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

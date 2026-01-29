"""Adaptive Cruise Control System implementation."""

import math
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that manages speed and distance to lead vehicle."""

    def __init__(self, config):
        """
        Initialize the ACC system.

        Args:
            config: Configuration dictionary with nested structure from vehicle_params.yaml
                   Expected keys: config['acc_settings'], config['vehicle'], etc.
        """
        # ACC Settings
        acc_settings = config["acc_settings"]
        self.set_speed = acc_settings["set_speed"]
        self.time_headway = acc_settings["time_headway"]
        self.min_distance = acc_settings["min_distance"]
        self.emergency_ttc_threshold = acc_settings["emergency_ttc_threshold"]

        # Vehicle constraints
        vehicle = config["vehicle"]
        self.max_accel = vehicle["max_acceleration"]
        self.max_decel = vehicle["max_deceleration"]

        # PID Controllers
        pid_speed_config = config.get("pid_speed", {})
        pid_distance_config = config.get("pid_distance", {})

        self.pid_speed = PIDController(
            pid_speed_config.get("kp", 0.1),
            pid_speed_config.get("ki", 0.01),
            pid_speed_config.get("kd", 0.0),
        )

        self.pid_distance = PIDController(
            pid_distance_config.get("kp", 0.1),
            pid_distance_config.get("ki", 0.01),
            pid_distance_config.get("kd", 0.0),
        )

        self.mode = "cruise"
        self.distance_error = 0.0

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
        """
        # If no lead vehicle detected, cruise at set speed
        if lead_speed is None or distance is None:
            self.mode = "cruise"
            self.distance_error = 0.0

            # Cruise control: maintain set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)

        else:
            # Lead vehicle detected - check for emergency conditions
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            if ttc is not None and ttc < self.emergency_ttc_threshold:
                # Emergency braking
                self.mode = "emergency"
                accel_cmd = self.max_decel
            else:
                # Normal follow mode
                self.mode = "follow"

                # Calculate desired distance based on time headway
                desired_distance = self.time_headway * ego_speed + self.min_distance

                # Distance error (positive means too far, negative means too close)
                self.distance_error = desired_distance - distance

                # PID control for distance
                accel_cmd = self.pid_distance.compute(self.distance_error, dt)

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, self.mode, self.distance_error

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """
        Compute Time To Collision (TTC).

        Args:
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            TTC in seconds, or None if closing rate is non-positive
        """
        closing_rate = ego_speed - lead_speed
        if closing_rate <= 0:
            return None
        return distance / closing_rate

    def reset(self):
        """Reset controller state."""
        self.pid_speed.reset()
        self.pid_distance.reset()
        self.mode = "cruise"
        self.distance_error = 0.0

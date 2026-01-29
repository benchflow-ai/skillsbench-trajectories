"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Configuration dictionary from vehicle_params.yaml with keys:
                    - 'acc_settings': dict with set_speed, time_headway, min_distance, emergency_ttc_threshold
                    - 'vehicle': dict with max_acceleration, max_deceleration
        """
        # Extract ACC settings
        acc_settings = config["acc_settings"]
        vehicle = config["vehicle"]

        self.set_speed = acc_settings["set_speed"]
        self.time_headway = acc_settings["time_headway"]
        self.min_distance = acc_settings["min_distance"]
        self.emergency_ttc_threshold = acc_settings["emergency_ttc_threshold"]

        self.max_acceleration = vehicle["max_acceleration"]
        self.max_deceleration = vehicle["max_deceleration"]

        # Load PID controller gains from config
        pid_speed_params = config["pid_speed"]
        pid_distance_params = config["pid_distance"]

        self.pid_speed = PIDController(
            pid_speed_params["kp"],
            pid_speed_params["ki"],
            pid_speed_params["kd"],
        )

        self.pid_distance = PIDController(
            pid_distance_params["kp"],
            pid_distance_params["ki"],
            pid_distance_params["kd"],
        )

        self.mode = "cruise"
        self.last_mode = "cruise"

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command for ACC.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no vehicle ahead
            distance: Distance to lead vehicle (m) or None if no vehicle ahead
            dt: Time step (seconds)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Acceleration command in m/s^2, clipped to limits
                - mode: Current operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error in meters (only when following)
        """
        distance_error = None

        # Determine mode and compute acceleration
        if lead_speed is None or distance is None:
            # No vehicle ahead, cruise at set speed
            self.mode = "cruise"
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
        else:
            # Vehicle ahead, check for emergency
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            if ttc is not None and ttc < self.emergency_ttc_threshold:
                # Emergency braking
                self.mode = "emergency"
                accel_cmd = self.max_deceleration
            else:
                # Normal following
                self.mode = "follow"
                # Desired distance: min_distance + time_headway * ego_speed
                desired_distance = self.min_distance + self.time_headway * ego_speed
                # Distance error: negative when gap is too small (actual < desired)
                distance_error = distance - desired_distance

                # Speed error: lead vehicle speed minus ego speed
                speed_error = lead_speed - ego_speed

                # Compute both control outputs
                distance_accel = self.pid_distance.compute(distance_error, dt)
                speed_accel = self.pid_speed.compute(speed_error, dt)

                # Blended control: Weighted combination with safety priority
                # Distance control is more important for safety
                # Weight increases as gap shrinks (distance_error becomes more negative)
                weight_distance = max(0, min(1.0, -distance_error / 20.0))  # 0 when gap is 20m+, 1 when gap is -1
                weight_speed = 1.0 - weight_distance

                accel_cmd = weight_distance * distance_accel + weight_speed * speed_accel

        # Clip acceleration to limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, self.mode, distance_error

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """
        Compute Time To Collision (TTC).

        Args:
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            TTC in seconds, or None if no collision threat
        """
        relative_velocity = ego_speed - lead_speed

        if relative_velocity <= 0:
            # Not closing gap
            return None

        if distance <= 0:
            # Already collided
            return 0.0

        ttc = distance / relative_velocity
        return ttc

    def reset(self):
        """Reset ACC system state."""
        self.pid_speed.reset()
        self.pid_distance.reset()
        self.mode = "cruise"

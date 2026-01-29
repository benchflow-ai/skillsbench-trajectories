"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    ACC system that maintains set speed or follows a lead vehicle at safe distance.

    Modes:
    - 'cruise': Free cruising at set speed (no lead vehicle)
    - 'follow': Following lead vehicle at safe distance
    - 'emergency': Emergency braking (TTC < threshold)
    """

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Configuration dict with keys:
                - acc_settings: dict with set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: dict with max_acceleration, max_deceleration
                - pid_speed: dict with kp, ki, kd for speed control
                - pid_distance: dict with kp, ki, kd for distance control
                - simulation: dict with dt (timestep)
        """
        self.config = config

        # Extract settings
        acc_settings = config["acc_settings"]
        vehicle = config["vehicle"]
        pid_speed_gains = config["pid_speed"]
        pid_distance_gains = config["pid_distance"]

        self.set_speed = acc_settings["set_speed"]
        self.time_headway = acc_settings["time_headway"]
        self.min_distance = acc_settings["min_distance"]
        self.emergency_ttc_threshold = acc_settings["emergency_ttc_threshold"]

        self.max_accel = vehicle["max_acceleration"]
        self.max_decel = vehicle["max_deceleration"]

        self.dt = config["simulation"]["dt"]

        # Initialize PID controllers
        self.pid_speed = PIDController(
            pid_speed_gains["kp"], pid_speed_gains["ki"], pid_speed_gains["kd"]
        )
        self.pid_distance = PIDController(
            pid_distance_gains["kp"],
            pid_distance_gains["ki"],
            pid_distance_gains["kd"],
        )

    def compute(self, ego_speed, lead_speed, distance):
        """
        Compute acceleration command for ACC system.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None
            distance: Distance to lead vehicle (m) or None

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: error in following distance (m) or None
        """
        # No lead vehicle detected - cruise at set speed
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, self.dt)
            accel_cmd = self._limit_acceleration(accel_cmd, ego_speed)
            return accel_cmd, "cruise", None

        # Lead vehicle detected - compute desired following distance
        desired_distance = self.min_distance + self.time_headway * ego_speed
        distance_error = desired_distance - distance

        # Compute TTC (Time To Collision)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0:
            ttc = distance / relative_speed
        else:
            ttc = float("inf")

        # Emergency braking if TTC is too low
        if ttc < self.emergency_ttc_threshold:
            accel_cmd = self.max_decel
            return accel_cmd, "emergency", distance_error

        # Normal following mode - use PID distance controller
        accel_cmd = self.pid_distance.compute(distance_error, self.dt)
        accel_cmd = self._limit_acceleration(accel_cmd, ego_speed)

        return accel_cmd, "follow", distance_error

    def _limit_acceleration(self, accel_cmd, ego_speed):
        """
        Limit acceleration within vehicle constraints.

        Args:
            accel_cmd: Commanded acceleration (m/s^2)
            ego_speed: Current speed (m/s)

        Returns:
            float: Limited acceleration (m/s^2)
        """
        # Clamp to vehicle limits
        accel_limited = max(self.max_decel, min(self.max_accel, accel_cmd))

        # Prevent negative speeds
        if ego_speed <= 0 and accel_limited < 0:
            accel_limited = 0

        return accel_limited

    def reset(self):
        """Reset PID controllers."""
        self.pid_speed.reset()
        self.pid_distance.reset()

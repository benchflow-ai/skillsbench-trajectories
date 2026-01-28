"""Adaptive Cruise Control (ACC) System."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or follows lead vehicles.

    Modes:
    - 'cruise': No lead vehicle, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe distance
    - 'emergency': TTC < threshold, maximum braking
    """

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Configuration dict with keys:
                - vehicle: dict with mass, max_acceleration, max_deceleration
                - acc_settings: dict with set_speed, time_headway, min_distance,
                               emergency_ttc_threshold
                - pid_speed: dict with kp, ki, kd for speed control
                - pid_distance: dict with kp, ki, kd for distance control
        """
        self.vehicle = config["vehicle"]
        self.settings = config["acc_settings"]

        self.set_speed = self.settings["set_speed"]
        self.time_headway = self.settings["time_headway"]
        self.min_distance = self.settings["min_distance"]
        self.emergency_ttc = self.settings["emergency_ttc_threshold"]

        self.max_accel = self.vehicle["max_acceleration"]
        self.max_decel = self.vehicle["max_deceleration"]

        # Initialize PID controllers
        pid_speed_gains = config["pid_speed"]
        pid_dist_gains = config["pid_distance"]

        self.pid_speed = PIDController(
            pid_speed_gains["kp"], pid_speed_gains["ki"], pid_speed_gains["kd"]
        )
        self.pid_distance = PIDController(
            pid_dist_gains["kp"], pid_dist_gains["ki"], pid_dist_gains["kd"]
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command for ACC control.

        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)

        Returns:
            Tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Command acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error in meters (None for cruise)
        """
        # Determine mode based on lead vehicle presence
        if lead_speed is None or distance is None:
            return self._cruise_mode(ego_speed, dt)

        # Calculate time-to-collision
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            ttc = float("inf")
        else:
            ttc = distance / relative_speed if distance > 0 else float("inf")

        # Check emergency condition
        if ttc < self.emergency_ttc and ttc >= 0:
            return self._emergency_mode(dt)

        # Normal follow mode
        return self._follow_mode(ego_speed, lead_speed, distance, ttc, dt)

    def _cruise_mode(self, ego_speed, dt):
        """
        Cruise mode: maintain set speed.

        Args:
            ego_speed: Current vehicle speed
            dt: Time step

        Returns:
            Tuple: (acceleration_cmd, mode, distance_error)
        """
        # Speed error: setpoint - actual
        speed_error = self.set_speed - ego_speed
        accel_cmd = self.pid_speed.compute(speed_error, dt)

        # Clamp to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, "cruise", None

    def _follow_mode(self, ego_speed, lead_speed, distance, ttc, dt):
        """
        Follow mode: maintain safe distance to lead vehicle.

        Uses dual-loop control: speed control to match lead, distance control for spacing.

        Args:
            ego_speed: Current vehicle speed
            lead_speed: Lead vehicle speed
            distance: Distance to lead vehicle
            ttc: Time-to-collision
            dt: Time step

        Returns:
            Tuple: (acceleration_cmd, mode, distance_error)
        """
        # Desired distance: min_distance + time_headway * lead_speed (more stable with lead velocity)
        desired_distance = self.min_distance + self.time_headway * lead_speed

        # Distance error (positive means too far, negative means too close)
        distance_error = desired_distance - distance

        # Primary control: distance error-based control (for safety)
        distance_cmd = self.pid_distance.compute(distance_error, dt)

        # Secondary control: match lead vehicle speed when distance is good
        # Only apply if distance error is small (within ±5m)
        if abs(distance_error) < 5.0:
            speed_error = lead_speed - ego_speed
            speed_cmd = self.pid_speed.compute(speed_error, dt)
            # Light speed control to maintain velocity synchronization
            accel_cmd = 0.2 * speed_cmd + 0.8 * distance_cmd
        else:
            # Distance error is large, prioritize distance control entirely
            accel_cmd = distance_cmd

        # Clamp to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, "follow", distance_error

    def _emergency_mode(self, dt):
        """
        Emergency mode: maximum braking.

        Args:
            dt: Time step (unused)

        Returns:
            Tuple: (acceleration_cmd, mode, distance_error)
        """
        # Maximum deceleration
        return self.max_decel, "emergency", None

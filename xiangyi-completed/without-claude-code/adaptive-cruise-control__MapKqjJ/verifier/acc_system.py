"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that maintains set speed or follows lead vehicle.

    Features:
    - Cruise mode: maintain set speed when no lead vehicle
    - Follow mode: maintain safe distance from lead vehicle
    - Emergency mode: trigger emergency braking if TTC < threshold
    """

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config: Dictionary containing vehicle and ACC settings
                    Must have keys:
                    - vehicle: {mass, max_acceleration, max_deceleration, ...}
                    - acc_settings: {set_speed, time_headway, min_distance,
                                    emergency_ttc_threshold}
                    - pid_speed: {kp, ki, kd}
                    - pid_distance: {kp, ki, kd}
        """
        self.vehicle_config = config["vehicle"]
        self.acc_settings = config["acc_settings"]

        # Extract constraints
        self.set_speed = self.acc_settings["set_speed"]
        self.time_headway = self.acc_settings["time_headway"]
        self.min_distance = self.acc_settings["min_distance"]
        self.emergency_ttc_threshold = self.acc_settings["emergency_ttc_threshold"]

        self.max_accel = self.vehicle_config["max_acceleration"]
        self.max_decel = self.vehicle_config["max_deceleration"]

        # Initialize PID controllers
        pid_speed_config = config.get("pid_speed", {})
        pid_distance_config = config.get("pid_distance", {})

        self.speed_pid = PIDController(
            kp=pid_speed_config.get("kp", 0.1),
            ki=pid_speed_config.get("ki", 0.01),
            kd=pid_speed_config.get("kd", 0.0),
        )

        self.distance_pid = PIDController(
            kp=pid_distance_config.get("kp", 0.1),
            ki=pid_distance_config.get("ki", 0.01),
            kd=pid_distance_config.get("kd", 0.0),
        )

        # State tracking
        self.current_mode = "cruise"

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on ACC logic.

        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Current ACC mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance control error (m) or None
        """
        distance_error = None

        # Determine mode and compute command
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            mode = "cruise"
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        else:
            # Lead vehicle detected - check for emergency condition first
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            if ttc is not None and ttc < self.emergency_ttc_threshold:
                # Emergency braking
                mode = "emergency"
                accel_cmd = self.max_decel
                distance_error = distance - (self.min_distance + self.time_headway * lead_speed)

            else:
                # Follow mode - maintain safe distance
                mode = "follow"
                # Desired distance based on time headway
                desired_distance = (
                    self.min_distance + self.time_headway * ego_speed
                )
                distance_error = distance - desired_distance

                # Use distance PID to compute acceleration
                accel_from_distance = self.distance_pid.compute(
                    distance_error, dt
                )

                # Also control speed toward lead vehicle speed with less weight
                speed_error = lead_speed - ego_speed
                accel_from_speed = self.speed_pid.compute(speed_error, dt) * 0.3

                # Combine both controls, with distance control as primary
                accel_cmd = accel_from_distance + accel_from_speed

        # Clamp acceleration to limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        self.current_mode = mode

        return accel_cmd, mode, distance_error

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """Compute Time To Collision (TTC).

        Args:
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            float: TTC in seconds, or None if not applicable
        """
        relative_speed = ego_speed - lead_speed

        if relative_speed <= 0:
            # Not closing in or moving at same speed
            return float("inf")

        if distance <= 0:
            return 0.0

        ttc = distance / relative_speed
        return ttc

    def reset_controllers(self):
        """Reset PID controller states."""
        self.speed_pid.reset()
        self.distance_pid.reset()

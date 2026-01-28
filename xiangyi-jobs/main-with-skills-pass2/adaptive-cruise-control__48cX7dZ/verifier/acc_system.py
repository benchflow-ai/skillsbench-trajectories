"""
Adaptive Cruise Control (ACC) system implementation.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    ACC system that maintains set speed and follows lead vehicles safely.
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Configuration dict containing:
                - acc_settings: ACC parameters (set_speed, time_headway, min_distance, emergency_ttc_threshold)
                - vehicle: Vehicle parameters (max_acceleration, max_deceleration)
                - pid_speed: Speed PID gains (kp, ki, kd)
                - pid_distance: Distance PID gains (kp, ki, kd)
        """
        self.set_speed = config["acc_settings"]["set_speed"]
        self.time_headway = config["acc_settings"]["time_headway"]
        self.min_distance = config["acc_settings"]["min_distance"]
        self.emergency_ttc = config["acc_settings"]["emergency_ttc_threshold"]

        self.max_accel = config["vehicle"]["max_acceleration"]
        self.max_decel = config["vehicle"]["max_deceleration"]

        # Initialize PID controllers
        speed_gains = config["pid_speed"]
        distance_gains = config["pid_distance"]

        self.pid_speed = PIDController(
            speed_gains["kp"], speed_gains["ki"], speed_gains["kd"]
        )
        self.pid_distance = PIDController(
            distance_gains["kp"], distance_gains["ki"], distance_gains["kd"]
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command for ACC.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Timestep in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration (m/s^2)
            - mode: Control mode ('cruise', 'follow', 'emergency')
            - distance_error: Error in distance (m) or None
        """
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise control mode
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)

            # Limit acceleration
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

            return accel_cmd, "cruise", None

        # Lead vehicle detected
        # Calculate desired distance based on time headway and minimum gap
        desired_distance = self.min_distance + self.time_headway * ego_speed

        # Calculate TTC (Time To Collision)
        if ego_speed > lead_speed and (ego_speed - lead_speed) > 1e-6:
            ttc = distance / (ego_speed - lead_speed)
        else:
            ttc = float("inf")

        # Check for emergency condition
        if ttc < self.emergency_ttc and ego_speed > lead_speed:
            # Emergency braking
            accel_cmd = self.max_decel
            return accel_cmd, "emergency", distance - desired_distance

        # Follow mode - use distance control
        distance_error = desired_distance - distance

        # Use speed control to reach set speed when far enough
        speed_error = self.set_speed - ego_speed

        # Compute both controls
        accel_from_distance = self.pid_distance.compute(distance_error, dt)
        accel_from_speed = self.pid_speed.compute(speed_error, dt)

        # Blend between speed and distance control
        # Safety-first approach: prioritize distance control to maintain safe spacing
        if distance_error > 1.0:
            # Too close - heavily weight distance control
            accel_cmd = 0.8 * accel_from_distance + 0.2 * accel_from_speed
        elif distance_error > -5.0:
            # Moderately close - balance both
            accel_cmd = 0.6 * accel_from_distance + 0.4 * accel_from_speed
        else:
            # Safe distance - prioritize reaching set speed
            accel_cmd = 0.2 * accel_from_distance + 0.8 * accel_from_speed

        # Limit acceleration
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, "follow", distance_error

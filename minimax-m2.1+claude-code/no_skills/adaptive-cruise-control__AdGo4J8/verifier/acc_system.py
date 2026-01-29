"""Adaptive Cruise Control System."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config: dict):
        """
        Initialize ACC system.

        Args:
            config: Nested dict from vehicle_params.yaml
        """
        # Extract vehicle parameters
        vehicle = config.get('vehicle', {})
        self.max_acceleration = vehicle.get('max_acceleration', 3.0)
        self.max_deceleration = vehicle.get('max_deceleration', -8.0)

        # Extract ACC settings
        acc_settings = config.get('acc_settings', {})
        self.set_speed = acc_settings.get('set_speed', 30.0)
        self.time_headway = acc_settings.get('time_headway', 1.5)
        self.min_distance = acc_settings.get('min_distance', 10.0)
        self.emergency_ttc_threshold = acc_settings.get('emergency_ttc_threshold', 3.0)

        # Extract PID gains
        pid_speed_config = config.get('pid_speed', {})
        pid_distance_config = config.get('pid_distance', {})

        self.speed_pid = PIDController(
            kp=pid_speed_config.get('kp', 0.1),
            ki=pid_speed_config.get('ki', 0.01),
            kd=pid_speed_config.get('kd', 0.0)
        )

        self.distance_pid = PIDController(
            kp=pid_distance_config.get('kp', 0.1),
            ki=pid_distance_config.get('ki', 0.01),
            kd=pid_distance_config.get('kd', 0.0)
        )

        # Current mode tracking
        self.current_mode = 'cruise'

    def reset(self):
        """Reset ACC system state."""
        self.speed_pid.reset()
        self.distance_pid.reset()
        self.current_mode = 'cruise'

    def compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Compute Time To Collision.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            Time To Collision in seconds, or float('inf') if no collision risk
        """
        relative_speed = lead_speed - ego_speed
        if distance <= 0:
            return 0.0
        if relative_speed >= 0:
            # Lead vehicle is moving away
            return float('inf')
        return abs(distance / relative_speed)

    def compute_desired_distance(self, ego_speed: float) -> float:
        """
        Compute desired following distance.

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            Desired distance in meters
        """
        return max(self.min_distance, ego_speed * self.time_headway)

    def compute(
        self,
        ego_speed: float,
        lead_speed: float | None,
        distance: float | None,
        dt: float,
        ref_speed: float = None
    ) -> tuple[float, str, float]:
        """
        Compute ACC control output.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (m), None if no lead vehicle
            dt: Time step (s)
            ref_speed: Reference speed from sensor data (used in cruise mode)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        distance_error = 0.0

        # Check for lead vehicle
        has_lead = lead_speed is not None and distance is not None and distance > 0

        if not has_lead:
            # No lead vehicle - cruise mode
            self.current_mode = 'cruise'

            # Use reference speed if available, otherwise use set_speed
            target_speed = ref_speed if ref_speed is not None else self.set_speed
            speed_error = target_speed - ego_speed
            acc_cmd = self.speed_pid.compute(speed_error, dt)
        else:
            # Lead vehicle present - compute TTC
            ttc = self.compute_ttc(ego_speed, lead_speed, distance)

            if ttc < self.emergency_ttc_threshold:
                # Emergency braking mode
                self.current_mode = 'emergency'
                acc_cmd = self.max_deceleration
                distance_error = distance - self.min_distance
            else:
                # Follow mode - maintain safe distance
                self.current_mode = 'follow'

                # Compute desired distance based on time headway
                desired_distance = self.compute_desired_distance(ego_speed)
                distance_error = distance - desired_distance

                # Combined speed and distance control
                # Target speed = lead_speed + correction for distance error
                # If distance > desired, we want to slow down (negative correction)
                # If distance < desired, we want to speed up (positive correction)
                distance_correction = -distance_error * 0.5  # Aggressive correction
                target_ego_speed = lead_speed + distance_correction

                # Clamp target speed
                target_ego_speed = max(0, min(self.set_speed, target_ego_speed))

                # Compute speed error and use speed PID
                speed_error = target_ego_speed - ego_speed
                acc_cmd = self.speed_pid.compute(speed_error, dt)

        # Apply acceleration limits
        acc_cmd = max(self.max_deceleration, min(self.max_acceleration, acc_cmd))

        return acc_cmd, self.current_mode, distance_error

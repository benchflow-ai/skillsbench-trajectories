"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config: dict):
        """Initialize ACC with configuration.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - vehicle: mass, max_acceleration, max_deceleration
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # PID controllers
        self.speed_controller = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd']
        )
        self.distance_controller = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd']
        )

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate desired following distance based on speed.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """Calculate Time-To-Collision.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            Time-to-collision in seconds (infinity if vehicles not closing)
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return float('inf')
        return distance / relative_speed

    def _clamp_acceleration(self, acceleration: float) -> float:
        """Clamp acceleration to vehicle limits.

        Args:
            acceleration: Desired acceleration in m/s^2

        Returns:
            Clamped acceleration within [max_deceleration, max_acceleration]
        """
        return max(self.max_deceleration, min(self.max_acceleration, acceleration))

    def compute(self, ego_speed: float, lead_speed: float, distance: float, dt: float) -> tuple:
        """Compute the acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s (None if no lead vehicle)
            distance: Distance to lead vehicle in meters (None if no lead vehicle)
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Acceleration command in m/s^2
            - mode: 'cruise', 'follow', or 'emergency'
            - distance_error: Error from desired following distance (None in cruise mode)
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

            # Anti-overshoot: reduce acceleration when approaching set speed
            if ego_speed > self.set_speed * 0.9 and accel_cmd > 0:
                # Proportionally reduce acceleration as we approach set speed
                reduction_factor = (self.set_speed - ego_speed) / (self.set_speed * 0.1)
                reduction_factor = max(0.0, min(1.0, reduction_factor))
                accel_cmd = accel_cmd * reduction_factor

            # If already at or above set speed, don't accelerate
            if ego_speed >= self.set_speed:
                accel_cmd = min(accel_cmd, 0.0)

            accel_cmd = self._clamp_acceleration(accel_cmd)
            # Reset distance controller when not in use
            self.distance_controller.reset()
            return (accel_cmd, 'cruise', None)

        # Calculate TTC for emergency detection
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Emergency mode: TTC below threshold
        if ttc < self.emergency_ttc_threshold:
            # Apply maximum braking
            accel_cmd = self.max_deceleration
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            # Reset controllers during emergency
            self.speed_controller.reset()
            self.distance_controller.reset()
            return (accel_cmd, 'emergency', distance_error)

        # Follow mode: maintain safe following distance
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Use distance controller for following
        # Positive error = too far, need to accelerate
        # Negative error = too close, need to decelerate
        distance_accel = self.distance_controller.compute(distance_error, dt)

        # Also consider matching lead vehicle speed for smooth following
        speed_error = lead_speed - ego_speed
        speed_match_accel = self.speed_controller.compute(speed_error, dt)

        # Safety-focused control strategy:
        # 1. If too close, prioritize deceleration
        # 2. If at safe distance, match lead speed
        # 3. Never exceed set speed

        if distance_error < -5.0:
            # Significantly too close: aggressive deceleration
            accel_cmd = min(distance_accel, -2.0)
        elif distance_error < 0:
            # Moderately too close: use distance controller
            accel_cmd = distance_accel
        else:
            # Safe distance: primarily match lead speed, with distance correction
            accel_cmd = 0.7 * speed_match_accel + 0.3 * distance_accel

        # Don't exceed set speed even when following
        if ego_speed >= self.set_speed and accel_cmd > 0:
            accel_cmd = 0.0

        # Limit acceleration when approaching set speed to prevent overshoot
        if ego_speed > self.set_speed * 0.9 and accel_cmd > 0:
            accel_cmd = min(accel_cmd, 1.0)

        accel_cmd = self._clamp_acceleration(accel_cmd)
        return (accel_cmd, 'follow', distance_error)

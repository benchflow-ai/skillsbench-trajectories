"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control modes."""

    def __init__(self, config: dict):
        """Initialize the ACC system.

        Args:
            config: Configuration dictionary from vehicle_params.yaml
                Expected structure:
                - acc_settings:
                    - set_speed: Target cruise speed (m/s)
                    - time_headway: Desired time gap (s)
                    - min_distance: Minimum following distance (m)
                    - emergency_ttc_threshold: TTC threshold for emergency braking (s)
                - vehicle:
                    - max_acceleration: Maximum acceleration (m/s^2)
                    - max_deceleration: Maximum deceleration (m/s^2)
                - pid_speed: PID gains for speed control
                - pid_distance: PID gains for distance control
        """
        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        # Vehicle limits
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers
        pid_speed_cfg = config['pid_speed']
        pid_distance_cfg = config['pid_distance']

        self.speed_controller = PIDController(
            kp=pid_speed_cfg['kp'],
            ki=pid_speed_cfg['ki'],
            kd=pid_speed_cfg['kd']
        )

        self.distance_controller = PIDController(
            kp=pid_distance_cfg['kp'],
            ki=pid_distance_cfg['ki'],
            kd=pid_distance_cfg['kd']
        )

        self._current_mode = 'cruise'

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate the desired following distance based on time headway.

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            Desired following distance (m)
        """
        return max(self.min_distance, self.time_headway * ego_speed)

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """Calculate Time-To-Collision.

        Args:
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            TTC in seconds, or infinity if not approaching
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')
        return distance / relative_speed

    def compute(self, ego_speed: float, lead_speed: float, distance: float, dt: float) -> tuple:
        """Compute the acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step (s)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration (m/s^2)
            - mode: Operating mode ('cruise', 'follow', or 'emergency')
            - distance_error: Distance error (m), or None in cruise mode
        """
        # No lead vehicle detected - cruise mode
        if lead_speed is None or distance is None:
            self._current_mode = 'cruise'
            # Reset distance controller when switching to cruise
            self.distance_controller.reset()

            # Speed control: error = set_speed - ego_speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

            # Clamp to vehicle limits
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

            return (accel_cmd, 'cruise', None)

        # Lead vehicle present - check for emergency
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        if ttc < self.emergency_ttc_threshold:
            self._current_mode = 'emergency'
            # Emergency braking - apply maximum deceleration
            accel_cmd = self.max_deceleration

            # Calculate distance error for reporting
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = distance - desired_distance

            return (accel_cmd, 'emergency', distance_error)

        # Normal following mode
        self._current_mode = 'follow'

        # Reset speed controller when in follow mode to prevent integral windup
        self.speed_controller.reset()

        # Calculate desired following distance
        desired_distance = self._calculate_desired_distance(ego_speed)

        # Distance error: positive means we're farther than desired (can speed up)
        # negative means we're closer than desired (need to slow down)
        distance_error = distance - desired_distance

        # Use distance controller for primary control
        accel_from_distance = self.distance_controller.compute(distance_error, dt)

        # Speed matching: adjust based on relative speed to lead vehicle
        # Positive when lead is faster (should speed up), negative when lead is slower
        speed_diff = lead_speed - ego_speed

        # Combine distance-based and speed-matching control
        # Distance control provides the base, speed matching provides damping
        accel_cmd = accel_from_distance + 0.5 * speed_diff

        # Apply speed limit based on proximity to set speed
        speed_margin = self.set_speed - ego_speed
        if speed_margin <= 0:
            # At or above set speed - only allow deceleration
            speed_overshoot = ego_speed - self.set_speed
            accel_cmd = min(accel_cmd, -0.5 * speed_overshoot)
        elif speed_margin < 2.0 and accel_cmd > 0:
            # Approaching set speed - reduce acceleration proportionally
            accel_cmd = min(accel_cmd, speed_margin * 0.5)

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return (accel_cmd, 'follow', distance_error)

    def reset(self):
        """Reset both PID controllers."""
        self.speed_controller.reset()
        self.distance_controller.reset()
        self._current_mode = 'cruise'

"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with three operating modes:
    - cruise: Maintain set speed when no lead vehicle detected
    - follow: Maintain safe following distance when lead vehicle present
    - emergency: Apply maximum braking when TTC is below threshold
    """

    def __init__(self, config: dict):
        """
        Initialize the ACC system.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # ACC settings
        acc_settings = config['acc_settings']
        self.set_speed = acc_settings['set_speed']
        self.time_headway = acc_settings['time_headway']
        self.min_distance = acc_settings['min_distance']
        self.emergency_ttc_threshold = acc_settings['emergency_ttc_threshold']

        # Vehicle limits
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers
        pid_speed_cfg = config['pid_speed']
        self.speed_controller = PIDController(
            kp=pid_speed_cfg['kp'],
            ki=pid_speed_cfg['ki'],
            kd=pid_speed_cfg['kd']
        )

        pid_distance_cfg = config['pid_distance']
        self.distance_controller = PIDController(
            kp=pid_distance_cfg['kp'],
            ki=pid_distance_cfg['ki'],
            kd=pid_distance_cfg['kd']
        )

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute desired following distance based on time headway."""
        return self.min_distance + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Compute Time-To-Collision.

        Returns:
            TTC in seconds, or float('inf') if vehicles are not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')
        return distance / relative_speed

    def compute(self, ego_speed: float, lead_speed: float, distance: float, dt: float) -> tuple:
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no vehicle detected
            distance: Distance to lead vehicle (m), None if no vehicle detected
            dt: Time step (s)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Distance error (m), None in cruise mode
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

            # Reset distance controller when in cruise mode
            self.distance_controller.reset()

            # Clamp to vehicle limits
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

            return (accel_cmd, 'cruise', None)

        # Compute TTC for emergency detection
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        # Emergency mode: TTC below threshold
        if ttc < self.emergency_ttc_threshold:
            # Reset controllers
            self.speed_controller.reset()
            self.distance_controller.reset()

            # Apply maximum braking
            return (self.max_deceleration, 'emergency', distance - self._compute_desired_distance(ego_speed))

        # Follow mode: maintain safe following distance
        desired_distance = self._compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Distance controller output
        distance_accel = self.distance_controller.compute(distance_error, dt)

        # Also consider speed matching with lead vehicle
        speed_error = lead_speed - ego_speed
        speed_accel = self.speed_controller.compute(speed_error, dt)

        # Combine: use distance control as primary, speed matching as secondary
        # If too close, prioritize distance control (negative distance_error)
        # If at good distance, allow speed to approach set speed if lead is faster
        if distance_error < 0:
            # Too close - prioritize slowing down
            accel_cmd = min(distance_accel, speed_accel)
        else:
            # Good distance - can accelerate but respect lead vehicle
            # Limit to not exceed set speed
            max_speed_accel = (self.set_speed - ego_speed) * 0.5  # Gentle approach to set speed
            accel_cmd = min(distance_accel, max_speed_accel)

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return (accel_cmd, 'follow', distance_error)

    def reset(self):
        """Reset all controllers."""
        self.speed_controller.reset()
        self.distance_controller.reset()

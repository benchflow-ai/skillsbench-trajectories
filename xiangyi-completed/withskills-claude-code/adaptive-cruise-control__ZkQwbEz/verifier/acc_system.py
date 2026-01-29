"""Adaptive Cruise Control System implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or follows lead vehicle.

    Modes:
    - 'cruise': No lead vehicle detected, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe following distance
    - 'emergency': TTC below threshold, apply maximum braking
    """

    def __init__(self, config: dict):
        """
        Initialize the ACC system.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                   - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                   - vehicle: max_acceleration, max_deceleration
                   - pid_speed: kp, ki, kd
                   - pid_distance: kp, ki, kd
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

        # PID controllers with anti-windup based on vehicle limits
        pid_speed = config['pid_speed']
        self.speed_controller = PIDController(
            kp=pid_speed['kp'],
            ki=pid_speed['ki'],
            kd=pid_speed['kd'],
            output_min=self.max_deceleration,
            output_max=self.max_acceleration
        )

        pid_distance = config['pid_distance']
        self.distance_controller = PIDController(
            kp=pid_distance['kp'],
            ki=pid_distance['ki'],
            kd=pid_distance['kd'],
            output_min=self.max_deceleration,
            output_max=self.max_acceleration
        )

        self._prev_mode = 'cruise'

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate the desired following distance based on speed and time headway."""
        return self.min_distance + self.time_headway * ego_speed

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Calculate Time-To-Collision.

        Returns:
            TTC in seconds, or float('inf') if vehicles are not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')
        return distance / relative_speed

    def compute(self, ego_speed: float, lead_speed, distance, dt: float):
        """
        Compute the ACC control command.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2), clamped to vehicle limits
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error in following distance (m) or None in cruise mode
        """
        # No lead vehicle - cruise mode
        if lead_speed is None or distance is None:
            # Reset distance controller when switching to cruise
            if self._prev_mode != 'cruise':
                self.distance_controller.reset()

            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

            # Limit acceleration as we approach set speed to reduce overshoot
            # When within 1.5 m/s of setpoint, reduce max accel proportionally
            if speed_error > 0 and speed_error < 1.5:
                accel_limit = self.max_acceleration * (speed_error / 1.5)
                accel_cmd = min(accel_cmd, max(0.1, accel_limit))

            # Don't accelerate when above set speed
            if speed_error < 0 and accel_cmd > 0:
                accel_cmd = 0.0

            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            self._prev_mode = 'cruise'
            return (accel_cmd, 'cruise', None)

        # Calculate TTC for emergency detection
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Emergency braking mode
        if ttc < self.emergency_ttc_threshold:
            accel_cmd = self.max_deceleration
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = desired_distance - distance
            # Reset controllers after emergency
            self.speed_controller.reset()
            self.distance_controller.reset()
            self._prev_mode = 'emergency'
            return (accel_cmd, 'emergency', distance_error)

        # Reset controllers when switching modes
        if self._prev_mode == 'cruise':
            self.speed_controller.reset()
        if self._prev_mode == 'emergency':
            self.speed_controller.reset()
            self.distance_controller.reset()

        # Follow mode - maintain safe following distance
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = desired_distance - distance
        # distance_error > 0 means we're too close, need to brake
        # distance_error < 0 means we're too far, can accelerate

        # Primary control: distance-based using gap error
        # Use negative error because positive error (too close) should yield braking
        distance_accel = -self.distance_controller.compute(distance_error, dt)

        # Secondary consideration: speed matching with lead
        # Compute a target speed based on lead speed and distance error
        # If too close, target speed should be lower than lead
        # If too far and safe, target speed can match lead (but not exceed set speed)
        target_speed = lead_speed
        if distance_error > 0:
            # Too close - reduce target speed to open gap
            target_speed = lead_speed - 0.5 * distance_error
        target_speed = min(target_speed, self.set_speed)
        target_speed = max(target_speed, 0.0)

        speed_error = target_speed - ego_speed
        speed_accel = self.speed_controller.compute(speed_error, dt)

        # Blend controllers based on situation
        if distance_error > 10.0:
            # Critical: very close - maximum braking
            accel_cmd = self.max_deceleration
        elif distance_error > 5.0:
            # Too close - prioritize distance control
            accel_cmd = min(distance_accel, speed_accel)
        elif distance_error > 0:
            # Slightly close - blend with distance priority
            accel_cmd = 0.6 * distance_accel + 0.4 * speed_accel
        else:
            # Safe distance - blend evenly
            accel_cmd = 0.5 * distance_accel + 0.5 * speed_accel

        # Final safety checks
        # Don't accelerate if already at or above set speed
        if ego_speed >= self.set_speed and accel_cmd > 0:
            accel_cmd = 0.0

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        self._prev_mode = 'follow'
        return (accel_cmd, 'follow', distance_error)

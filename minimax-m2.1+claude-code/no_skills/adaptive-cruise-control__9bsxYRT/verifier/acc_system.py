"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config: dict):
        """
        Initialize the ACC system.

        Args:
            config: Configuration dictionary from vehicle_params.yaml
        """
        # Extract configuration
        acc_settings = config['acc_settings']
        pid_speed_config = config.get('pid_speed', {})
        pid_distance_config = config.get('pid_distance', {})

        # ACC parameters
        self.set_speed = acc_settings['set_speed']  # Target cruise speed (m/s)
        self.time_headway = acc_settings['time_headway']  # Time gap (s)
        self.min_distance = acc_settings['min_distance']  # Minimum gap (m)
        self.ttc_threshold = acc_settings['emergency_ttc_threshold']  # Emergency TTC threshold (s)

        # Vehicle limits
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers with acceleration limits
        acc_limits = (self.max_deceleration, self.max_acceleration)
        self.speed_pid = PIDController(
            kp=pid_speed_config.get('kp', 0.1),
            ki=pid_speed_config.get('ki', 0.01),
            kd=pid_speed_config.get('kd', 0.0),
            output_limits=acc_limits
        )
        self.distance_pid = PIDController(
            kp=pid_distance_config.get('kp', 0.1),
            ki=pid_distance_config.get('ki', 0.01),
            kd=pid_distance_config.get('kd', 0.0),
            output_limits=acc_limits
        )

    def compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Calculate Time To Collision (TTC).

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            Time to collision in seconds (float('inf') if approaching stationary lead)
        """
        relative_speed = ego_speed - lead_speed

        # No collision threat if lead is ahead and moving away or at same speed
        if relative_speed <= 0:
            return float('inf')

        # Calculate TTC
        ttc = distance / relative_speed
        return ttc

    def compute_desired_distance(self, ego_speed: float) -> float:
        """
        Calculate the desired following distance based on time headway.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)

        Returns:
            Desired following distance in meters
        """
        return max(self.min_distance, ego_speed * self.time_headway)

    def compute(
        self,
        ego_speed: float,
        lead_speed: float | None,
        distance: float | None,
        dt: float
    ) -> tuple[float, str, float]:
        """
        Compute the acceleration command based on current conditions.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (m), None if no lead vehicle
            dt: Time step (s)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration (m/s^2)
            - mode: Operating mode ('cruise', 'follow', 'emergency')
            - distance_error: Error in following distance (m, negative means too close)
        """
        # Default values
        acceleration_cmd = 0.0
        mode = 'cruise'
        distance_error = 0.0

        # Check for lead vehicle presence
        has_lead = lead_speed is not None and distance is not None and distance > 0

        if not has_lead:
            # No lead vehicle: maintain set speed using speed control
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)

        else:
            # Lead vehicle present: compute TTC
            ttc = self.compute_ttc(ego_speed, lead_speed, distance)

            if ttc < self.ttc_threshold:
                # Emergency braking mode
                mode = 'emergency'
                # Maximum deceleration for emergency braking
                acceleration_cmd = self.max_deceleration
                distance_error = distance - self.min_distance
            else:
                # Following mode: maintain safe distance
                mode = 'follow'
                desired_distance = self.compute_desired_distance(ego_speed)
                distance_error = distance - desired_distance

                # Compute speed error relative to lead vehicle
                lead_speed_error = lead_speed - ego_speed

                if distance > desired_distance:
                    # We're too far from lead vehicle: use speed PID to approach lead speed
                    # This naturally closes the gap while not exceeding lead speed
                    acceleration_cmd = self.speed_pid.compute(lead_speed_error, dt)
                else:
                    # We're too close: use distance PID to back off
                    # Negative distance_error means we need to slow down
                    acceleration_cmd = self.distance_pid.compute(distance_error, dt)

        # Apply acceleration limits (redundant but safe - PID already has limits)
        acceleration_cmd = max(
            self.max_deceleration,
            min(self.max_acceleration, acceleration_cmd)
        )

        return acceleration_cmd, mode, distance_error

"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml
                    e.g., config['acc_settings']['set_speed']
        """
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        self.pid_speed = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Control mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error (m) or None
        """
        # No lead vehicle - cruise mode
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            acceleration_cmd = self._clamp_acceleration(acceleration_cmd)
            return (acceleration_cmd, 'cruise', None)

        # Calculate Time-To-Collision (TTC)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency braking mode
        if ttc < self.emergency_ttc_threshold:
            acceleration_cmd = self.max_deceleration
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            return (acceleration_cmd, 'emergency', distance_error)

        # Follow mode - maintain safe following distance
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Use distance controller to generate target speed adjustment
        speed_adjustment = self.pid_distance.compute(distance_error, dt)
        target_speed = lead_speed + speed_adjustment

        # Limit target speed to set speed
        target_speed = min(target_speed, self.set_speed)

        # Use speed controller to track target speed
        speed_error = target_speed - ego_speed
        acceleration_cmd = self.pid_speed.compute(speed_error, dt)
        acceleration_cmd = self._clamp_acceleration(acceleration_cmd)

        return (acceleration_cmd, 'follow', distance_error)

    def _calculate_desired_distance(self, ego_speed):
        """Calculate desired following distance based on time headway.

        Args:
            ego_speed: Current vehicle speed (m/s)

        Returns:
            Desired distance (m)
        """
        return max(self.min_distance, self.time_headway * ego_speed)

    def _clamp_acceleration(self, acceleration):
        """Clamp acceleration to vehicle limits.

        Args:
            acceleration: Desired acceleration (m/s^2)

        Returns:
            Clamped acceleration (m/s^2)
        """
        return max(self.max_deceleration, min(self.max_acceleration, acceleration))

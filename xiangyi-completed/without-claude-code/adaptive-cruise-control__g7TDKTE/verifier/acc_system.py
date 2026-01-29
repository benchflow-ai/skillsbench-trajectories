"""Adaptive Cruise Control System."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Configuration dict with structure from vehicle_params.yaml
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle limits
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers (will be initialized with tuned parameters)
        self.speed_pid = None
        self.distance_pid = None

    def set_pid_controllers(self, speed_pid, distance_pid):
        """
        Set PID controllers with tuned parameters.

        Args:
            speed_pid: PIDController for speed control
            distance_pid: PIDController for distance control
        """
        self.speed_pid = speed_pid
        self.distance_pid = distance_pid

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error (m) or None if in cruise mode
        """
        # No lead vehicle - cruise mode
        if lead_speed is None or distance is None:
            return self._cruise_control(ego_speed, dt)

        # Calculate Time-To-Collision (TTC)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency mode - TTC below threshold
        if ttc < self.emergency_ttc_threshold:
            return self._emergency_braking(ego_speed, lead_speed, distance, dt)

        # Follow mode - maintain safe following distance
        return self._follow_control(ego_speed, lead_speed, distance, dt)

    def _cruise_control(self, ego_speed, dt):
        """
        Cruise control mode - maintain set speed.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'cruise', None)
        """
        # Speed error
        speed_error = self.set_speed - ego_speed

        # Compute acceleration using speed PID
        acceleration = self.speed_pid.compute(speed_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration = max(self.max_deceleration, min(self.max_acceleration, acceleration))

        return (acceleration, 'cruise', None)

    def _follow_control(self, ego_speed, lead_speed, distance, dt):
        """
        Follow control mode - maintain safe following distance.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'follow', distance_error)
        """
        # Desired following distance (time headway + minimum gap)
        desired_distance = ego_speed * self.time_headway + self.min_distance

        # Distance error
        distance_error = distance - desired_distance

        # Compute desired speed adjustment using distance PID
        speed_adjustment = self.distance_pid.compute(distance_error, dt)

        # Target speed is lead speed plus adjustment
        target_speed = lead_speed + speed_adjustment

        # Don't exceed set speed
        target_speed = min(target_speed, self.set_speed)

        # Speed error
        speed_error = target_speed - ego_speed

        # Compute acceleration using speed PID
        acceleration = self.speed_pid.compute(speed_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration = max(self.max_deceleration, min(self.max_acceleration, acceleration))

        return (acceleration, 'follow', distance_error)

    def _emergency_braking(self, ego_speed, lead_speed, distance, dt):
        """
        Emergency braking mode - apply maximum braking.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'emergency', distance_error)
        """
        # Desired following distance
        desired_distance = ego_speed * self.time_headway + self.min_distance

        # Distance error
        distance_error = distance - desired_distance

        # Apply aggressive braking proportional to distance error
        # Use distance PID but with higher gain for emergency
        speed_adjustment = self.distance_pid.compute(distance_error, dt)

        # Target speed is lead speed plus adjustment
        target_speed = lead_speed + speed_adjustment

        # Speed error
        speed_error = target_speed - ego_speed

        # Compute acceleration
        acceleration = self.speed_pid.compute(speed_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration = max(self.max_deceleration, min(self.max_acceleration, acceleration))

        # In emergency, bias toward stronger braking
        if acceleration > 0:
            acceleration = 0

        return (acceleration, 'emergency', distance_error)

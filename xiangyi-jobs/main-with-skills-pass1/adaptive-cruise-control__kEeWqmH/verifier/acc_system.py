from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or follows a lead vehicle.
    """

    def __init__(self, config):
        """
        Initialize the ACC system.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd for speed controller
                - pid_distance: kp, ki, kd for distance controller
        """
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )
        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error in following distance (m), or None in cruise mode
        """
        # No lead vehicle detected - cruise control mode
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
            acceleration_cmd = self._clamp_acceleration(acceleration_cmd)
            return (acceleration_cmd, 'cruise', None)

        # Calculate time-to-collision (TTC)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency mode - TTC below threshold OR distance critically low
        if ttc < self.emergency_ttc_threshold or distance < self.min_distance:
            # Apply maximum deceleration
            acceleration_cmd = self.max_deceleration
            desired_distance = self.time_headway * ego_speed + self.min_distance
            distance_error = distance - desired_distance
            return (acceleration_cmd, 'emergency', distance_error)

        # Follow mode - maintain safe following distance
        desired_distance = self.time_headway * ego_speed + self.min_distance
        distance_error = distance - desired_distance

        # Use distance controller to determine target acceleration
        acceleration_cmd = self.distance_pid.compute(distance_error, dt)

        # Additional safety: if distance is critically low, apply stronger braking
        if distance < self.min_distance:
            # Emergency braking proportional to how far below min distance
            safety_brake = -2.0 * (self.min_distance - distance)
            acceleration_cmd = min(acceleration_cmd, safety_brake)

        acceleration_cmd = self._clamp_acceleration(acceleration_cmd)

        return (acceleration_cmd, 'follow', distance_error)

    def _clamp_acceleration(self, acceleration):
        """Clamp acceleration to vehicle limits."""
        return max(self.max_deceleration, min(self.max_acceleration, acceleration))

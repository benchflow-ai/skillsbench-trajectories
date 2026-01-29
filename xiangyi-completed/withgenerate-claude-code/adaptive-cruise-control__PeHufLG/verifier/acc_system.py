"""Adaptive Cruise Control System Implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with multiple operating modes.

    Modes:
    - cruise: Maintain set speed when no vehicle ahead
    - follow: Maintain safe following distance behind lead vehicle
    - emergency: Apply maximum braking when collision imminent
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration parameters.

        Args:
            config (dict): Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd for speed controller
                - pid_distance: kp, ki, kd for distance controller
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle limits
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers
        speed_params = config['pid_speed']
        self.speed_pid = PIDController(
            kp=speed_params['kp'],
            ki=speed_params['ki'],
            kd=speed_params['kd']
        )

        distance_params = config['pid_distance']
        self.distance_pid = PIDController(
            kp=distance_params['kp'],
            ki=distance_params['ki'],
            kd=distance_params['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed (float): Current speed of ego vehicle (m/s)
            lead_speed (float or None): Speed of lead vehicle (m/s), None if no vehicle
            distance (float or None): Distance to lead vehicle (m), None if no vehicle
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration (m/s²)
                - mode (str): Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error (float or None): Distance error in follow mode, None otherwise
        """
        # Select operating mode
        mode = self._select_mode(lead_speed, distance, ego_speed)

        # Compute acceleration based on mode
        if mode == 'cruise':
            acceleration_cmd = self._cruise_control(ego_speed, dt)
            distance_error = None

        elif mode == 'follow':
            acceleration_cmd, distance_error = self._follow_control(
                ego_speed, lead_speed, distance, dt
            )

        else:  # emergency
            acceleration_cmd = self.max_deceleration
            desired_distance = self.time_headway * ego_speed + self.min_distance
            distance_error = distance - desired_distance

        # Apply acceleration limits
        acceleration_cmd = max(
            self.max_deceleration,
            min(self.max_acceleration, acceleration_cmd)
        )

        return acceleration_cmd, mode, distance_error

    def _select_mode(self, lead_speed, distance, ego_speed):
        """
        Select operating mode based on traffic conditions.

        Args:
            lead_speed (float or None): Speed of lead vehicle
            distance (float or None): Distance to lead vehicle
            ego_speed (float): Current ego speed

        Returns:
            str: Operating mode ('cruise', 'follow', or 'emergency')
        """
        # No vehicle detected - cruise mode
        if lead_speed is None:
            return 'cruise'

        # Calculate Time-To-Collision (TTC)
        relative_speed = ego_speed - lead_speed

        # Check for emergency situation
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
            if ttc < self.emergency_ttc_threshold:
                return 'emergency'

        # Follow mode (vehicle detected, not emergency)
        return 'follow'

    def _cruise_control(self, ego_speed, dt):
        """
        Cruise control mode - maintain set speed.

        Args:
            ego_speed (float): Current ego speed (m/s)
            dt (float): Time step (seconds)

        Returns:
            float: Acceleration command (m/s²)
        """
        speed_error = self.set_speed - ego_speed
        acceleration = self.speed_pid.compute(speed_error, dt)
        return acceleration

    def _follow_control(self, ego_speed, lead_speed, distance, dt):
        """
        Follow control mode - maintain safe following distance.

        Args:
            ego_speed (float): Current ego speed (m/s)
            lead_speed (float): Lead vehicle speed (m/s)
            distance (float): Distance to lead vehicle (m)
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration, distance_error)
        """
        # Calculate desired following distance
        desired_distance = self.time_headway * ego_speed + self.min_distance

        # Distance error (positive = too far, negative = too close)
        distance_error = distance - desired_distance

        # Use distance PID to compute acceleration
        acceleration = self.distance_pid.compute(distance_error, dt)

        return acceleration, distance_error

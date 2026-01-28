"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system that manages vehicle speed and following distance.

    The system operates in three modes:
    - 'cruise': Maintains target speed when no lead vehicle detected
    - 'follow': Adjusts speed to maintain safe following distance when lead vehicle present
    - 'emergency': Applies emergency deceleration when TTC (Time-To-Collision) is critical
    """

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config (dict): Configuration dictionary with nested structure:
                - config['vehicle']['max_acceleration']
                - config['vehicle']['max_deceleration']
                - config['acc_settings']['set_speed']
                - config['acc_settings']['time_headway']
                - config['acc_settings']['min_distance']
                - config['acc_settings']['emergency_ttc_threshold']
                - config['pid_speed'][kp, ki, kd]
                - config['pid_distance'][kp, ki, kd]
        """
        self.config = config

        # Vehicle constraints
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Initialize PID controllers for speed and distance
        pid_speed_gains = config['pid_speed']
        pid_distance_gains = config['pid_distance']

        self.pid_speed = PIDController(
            pid_speed_gains['kp'],
            pid_speed_gains['ki'],
            pid_speed_gains['kd']
        )

        self.pid_distance = PIDController(
            pid_distance_gains['kp'],
            pid_distance_gains['ki'],
            pid_distance_gains['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed (float): Current ego vehicle speed in m/s
            lead_speed (float or None): Lead vehicle speed in m/s (None if no lead vehicle)
            distance (float or None): Distance to lead vehicle in meters (None if no lead vehicle)
            dt (float): Time step in seconds

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Acceleration command in m/s^2
                - mode (str): 'cruise', 'follow', or 'emergency'
                - distance_error (float or None): Error in distance control
        """
        # Case 1: No lead vehicle detected - cruise control mode
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            accel_cmd = self._limit_acceleration(accel_cmd)
            return accel_cmd, 'cruise', None

        # Compute Time-To-Collision (TTC)
        relative_speed = ego_speed - lead_speed
        ttc = self._compute_ttc(distance, relative_speed)

        # Case 2: Emergency braking if TTC is critical
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            accel_cmd = self.max_decel
            return accel_cmd, 'emergency', None

        # Case 3: Follow mode - maintain safe following distance
        # Safe distance = min(time_headway * lead_speed, min_distance)
        target_distance = max(self.time_headway * lead_speed, self.min_distance)
        distance_error = target_distance - distance

        # Use distance error to control speed
        accel_cmd = self.pid_distance.compute(distance_error, dt)
        accel_cmd = self._limit_acceleration(accel_cmd)

        return accel_cmd, 'follow', distance_error

    def _compute_ttc(self, distance, relative_speed):
        """Compute Time-To-Collision.

        Args:
            distance (float): Current distance to lead vehicle
            relative_speed (float): Ego speed - lead speed

        Returns:
            float or None: TTC in seconds, None if no collision predicted
        """
        if relative_speed <= 0:
            return None  # Moving away or same speed
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def _limit_acceleration(self, accel):
        """Limit acceleration to physical constraints.

        Args:
            accel (float): Requested acceleration

        Returns:
            float: Limited acceleration within [max_decel, max_accel]
        """
        return max(self.max_decel, min(self.max_accel, accel))

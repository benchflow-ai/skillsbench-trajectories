"""
Adaptive Cruise Control (ACC) system implementation.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed and safe following distance.

    Modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': TTC < threshold, apply maximum deceleration

    Attributes:
        set_speed (float): Target cruise speed (m/s)
        time_headway (float): Desired time gap behind lead vehicle (s)
        min_distance (float): Minimum safe distance (m)
        emergency_ttc_threshold (float): TTC threshold for emergency braking (s)
        max_acceleration (float): Maximum acceleration limit (m/s²)
        max_deceleration (float): Maximum deceleration limit (m/s²)
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config (dict): Configuration dictionary with nested structure:
                config['acc_settings']['set_speed']
                config['acc_settings']['time_headway']
                config['acc_settings']['min_distance']
                config['acc_settings']['emergency_ttc_threshold']
                config['vehicle']['max_acceleration']
                config['vehicle']['max_deceleration']
                config['pid_speed']['kp/ki/kd']
                config['pid_distance']['kp/ki/kd']
        """
        # Load ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Load vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers for speed and distance control
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
        Compute acceleration command based on sensor inputs and vehicle state.

        Args:
            ego_speed (float): Current vehicle speed (m/s)
            lead_speed (float or None): Lead vehicle speed (m/s), None if no lead vehicle
            distance (float or None): Distance to lead vehicle (m), None if no lead vehicle
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Acceleration command (m/s²)
                - mode (str): Current control mode ('cruise', 'follow', or 'emergency')
                - distance_error (float or None): Distance error in follow mode, None otherwise
        """
        # No lead vehicle detected - cruise mode
        if lead_speed is None or distance is None:
            return self._cruise_mode(ego_speed, dt)

        # Check for emergency condition
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
            if ttc < self.emergency_ttc_threshold:
                return self._emergency_mode()

        # Normal follow mode
        return self._follow_mode(ego_speed, lead_speed, distance, dt)

    def _cruise_mode(self, ego_speed, dt):
        """
        Cruise mode: maintain set speed when no lead vehicle detected.

        Args:
            ego_speed (float): Current vehicle speed (m/s)
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'cruise', None)
        """
        # Compute speed error
        speed_error = self.set_speed - ego_speed

        # Compute control action from speed PID
        accel = self.speed_pid.compute(speed_error, dt)

        # Clamp to acceleration limits
        accel = max(min(accel, self.max_acceleration), self.max_deceleration)

        return accel, 'cruise', None

    def _follow_mode(self, ego_speed, lead_speed, distance, dt):
        """
        Follow mode: maintain safe following distance behind lead vehicle.

        Args:
            ego_speed (float): Current vehicle speed (m/s)
            lead_speed (float): Lead vehicle speed (m/s)
            distance (float): Current distance to lead vehicle (m)
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'follow', distance_error)
        """
        # Compute desired following distance based on time headway
        # desirable_distance = time_headway * speed + minimum_gap
        desired_distance = self.time_headway * ego_speed + self.min_distance

        # Compute distance error
        distance_error = desired_distance - distance

        # Compute acceleration to correct distance error
        distance_accel = self.distance_pid.compute(distance_error, dt)

        # Blend distance control with speed control
        # Weight distance control higher to prioritize safe following
        speed_error = self.set_speed - ego_speed
        speed_accel = self.speed_pid.compute(speed_error, dt)

        # Weighted blend: prioritize distance control when closing gap
        if distance_error > 0:
            # Need to slow down - increase weight of distance control
            accel = 0.3 * speed_accel + 0.7 * distance_accel
        else:
            # Distance OK - increase weight of speed control
            accel = 0.7 * speed_accel + 0.3 * distance_accel

        # Clamp to acceleration limits
        accel = max(min(accel, self.max_acceleration), self.max_deceleration)

        return accel, 'follow', distance_error

    def _emergency_mode(self):
        """
        Emergency mode: apply maximum deceleration when TTC < threshold.

        Returns:
            tuple: (max_deceleration, 'emergency', None)
        """
        return self.max_deceleration, 'emergency', None

    def reset(self):
        """Reset all controller states."""
        self.speed_pid.reset()
        self.distance_pid.reset()

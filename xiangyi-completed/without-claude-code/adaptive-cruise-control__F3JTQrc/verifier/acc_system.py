"""Adaptive Cruise Control System implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control (ACC) system.

    The ACC maintains set speed when no lead vehicle is present and adjusts
    speed to maintain safe following distance when a lead vehicle is detected.

    Operating modes:
    - 'cruise': No lead vehicle, maintain set speed
    - 'follow': Lead vehicle present, maintain safe following distance
    - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Dictionary containing vehicle and ACC settings with structure:
                {
                    'vehicle': {'max_acceleration': ..., 'max_deceleration': ...},
                    'acc_settings': {
                        'set_speed': ...,
                        'time_headway': ...,
                        'min_distance': ...,
                        'emergency_ttc_threshold': ...
                    }
                }
        """
        # Extract configuration
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers will be set externally after tuning
        self.speed_pid = None
        self.distance_pid = None

    def set_speed_pid(self, kp, ki, kd):
        """Set speed PID controller with gains."""
        self.speed_pid = PIDController(kp, ki, kd)

    def set_distance_pid(self, kp, ki, kd):
        """Set distance PID controller with gains."""
        self.distance_pid = PIDController(kp, ki, kd)

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control output.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Current operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error in following distance (m), or None in cruise mode
        """
        # Mode 1: Cruise control (no lead vehicle)
        if lead_speed is None or distance is None:
            return self._cruise_mode(ego_speed, dt)

        # Calculate Time-To-Collision (TTC)
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Mode 2: Emergency braking (TTC below threshold)
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            return self._emergency_mode(ego_speed, lead_speed, distance)

        # Mode 3: Following mode (lead vehicle present)
        return self._follow_mode(ego_speed, lead_speed, distance, dt)

    def _cruise_mode(self, ego_speed, dt):
        """
        Cruise control mode - maintain set speed.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, 'cruise', None)
        """
        speed_error = self.set_speed - ego_speed
        acceleration = self.speed_pid.compute(speed_error, dt)
        acceleration = self._clip_acceleration(acceleration)
        return (acceleration, 'cruise', None)

    def _follow_mode(self, ego_speed, lead_speed, distance, dt):
        """
        Following mode - maintain safe following distance.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Current distance to lead vehicle (m)
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, 'follow', distance_error)
        """
        # Calculate desired following distance using time headway
        desired_distance = self.min_distance + self.time_headway * ego_speed

        # Distance error (positive means we're too far, negative means too close)
        distance_error = distance - desired_distance

        # Use distance PID to compute acceleration directly
        # Positive error (too far) -> positive acceleration (speed up)
        # Negative error (too close) -> negative acceleration (slow down)
        acceleration = self.distance_pid.compute(distance_error, dt)

        # Don't exceed set speed even in follow mode
        if ego_speed >= self.set_speed and acceleration > 0:
            acceleration = 0.0

        acceleration = self._clip_acceleration(acceleration)
        return (acceleration, 'follow', distance_error)

    def _emergency_mode(self, ego_speed, lead_speed, distance):
        """
        Emergency braking mode - apply maximum deceleration.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Current distance to lead vehicle (m)

        Returns:
            tuple: (max_deceleration, 'emergency', distance_error)
        """
        desired_distance = self.min_distance + self.time_headway * ego_speed
        distance_error = distance - desired_distance

        # Apply maximum braking
        return (self.max_deceleration, 'emergency', distance_error)

    def _calculate_ttc(self, ego_speed, lead_speed, distance):
        """
        Calculate Time-To-Collision (TTC).

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            float or None: TTC in seconds, or None if vehicles are diverging
        """
        relative_speed = ego_speed - lead_speed

        # If relative speed is <= 0, vehicles are diverging or matching speed
        if relative_speed <= 0:
            return None

        # TTC = distance / relative_speed
        ttc = distance / relative_speed
        return ttc

    def _clip_acceleration(self, acceleration):
        """
        Clip acceleration to vehicle limits.

        Args:
            acceleration: Requested acceleration (m/s^2)

        Returns:
            float: Clipped acceleration within [max_deceleration, max_acceleration]
        """
        return max(self.max_deceleration, min(self.max_acceleration, acceleration))

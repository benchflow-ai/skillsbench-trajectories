"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that manages speed and following distance.

    Modes:
    - cruise: No lead vehicle detected, maintain set speed
    - follow: Lead vehicle detected, maintain safe following distance
    - emergency: TTC below threshold, emergency braking
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
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
        self.speed_controller = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_controller = PIDController(
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
                - mode: Current mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error in following distance (m), or None if in cruise mode
        """
        # Check if lead vehicle is present
        if lead_speed is None or distance is None:
            # Cruise mode: No lead vehicle, maintain set speed
            return self._cruise_mode(ego_speed, dt)

        # Calculate time-to-collision (TTC)
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Check for emergency braking condition
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency mode: Apply maximum deceleration
            return self._emergency_mode(ego_speed, lead_speed, distance)

        # Follow mode: Maintain safe following distance
        return self._follow_mode(ego_speed, lead_speed, distance, dt)

    def _cruise_mode(self, ego_speed, dt):
        """
        Cruise mode: Maintain set speed.

        Args:
            ego_speed: Current speed (m/s)
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'cruise', None)
        """
        speed_error = self.set_speed - ego_speed
        acceleration_cmd = self.speed_controller.compute(speed_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return (acceleration_cmd, 'cruise', None)

    def _follow_mode(self, ego_speed, lead_speed, distance, dt):
        """
        Follow mode: Maintain safe following distance.

        Args:
            ego_speed: Current speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, 'follow', distance_error)
        """
        # Calculate desired following distance
        desired_distance = self.min_distance + self.time_headway * ego_speed

        # Distance error (positive means too close, negative means too far)
        distance_error = desired_distance - distance

        # Use distance controller to compute acceleration (negate because positive error means decelerate)
        acceleration_cmd = -self.distance_controller.compute(distance_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return (acceleration_cmd, 'follow', distance_error)

    def _emergency_mode(self, ego_speed, lead_speed, distance):
        """
        Emergency mode: Apply maximum deceleration.

        Args:
            ego_speed: Current speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            tuple: (acceleration_cmd, 'emergency', distance_error)
        """
        # Calculate desired following distance
        desired_distance = self.min_distance + self.time_headway * ego_speed
        distance_error = desired_distance - distance

        # Apply maximum deceleration
        acceleration_cmd = self.max_deceleration

        return (acceleration_cmd, 'emergency', distance_error)

    def _calculate_ttc(self, ego_speed, lead_speed, distance):
        """
        Calculate time-to-collision.

        Args:
            ego_speed: Current speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            float or None: TTC in seconds, or None if vehicles not approaching
        """
        relative_speed = ego_speed - lead_speed

        # Only calculate TTC if ego vehicle is approaching lead vehicle
        if relative_speed > 0:
            return distance / relative_speed

        return None

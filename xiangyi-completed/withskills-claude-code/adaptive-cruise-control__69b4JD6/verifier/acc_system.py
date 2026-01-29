"""Adaptive Cruise Control System."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with speed and distance control.

    The ACC system operates in three modes:
    - cruise: Maintains set speed when no lead vehicle is detected
    - follow: Maintains safe following distance when lead vehicle is present
    - emergency: Emergency braking when TTC is below threshold
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Dictionary containing nested configuration from vehicle_params.yaml
                   Expected keys: 'acc_settings', 'vehicle', 'pid_speed', 'pid_distance'
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        speed_pid = config['pid_speed']
        self.speed_controller = PIDController(
            kp=speed_pid['kp'],
            ki=speed_pid['ki'],
            kd=speed_pid['kd']
        )

        distance_pid = config['pid_distance']
        self.distance_controller = PIDController(
            kp=distance_pid['kp'],
            ki=distance_pid['ki'],
            kd=distance_pid['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Control mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error in following distance (m) or None
        """
        # Determine if lead vehicle is present
        if lead_speed is None or distance is None:
            # Cruise mode: no lead vehicle detected
            return self._cruise_mode(ego_speed, dt)

        # Calculate Time-To-Collision (TTC)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Check for emergency braking condition
        if ttc < self.emergency_ttc_threshold:
            return self._emergency_mode(ego_speed, lead_speed, distance, dt)

        # Follow mode: maintain safe following distance
        return self._follow_mode(ego_speed, lead_speed, distance, dt)

    def _cruise_mode(self, ego_speed, dt):
        """
        Cruise mode: maintain set speed.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, 'cruise', None)
        """
        speed_error = self.set_speed - ego_speed
        acceleration_cmd = self.speed_controller.compute(speed_error, dt)

        # Apply acceleration limits
        acceleration_cmd = max(self.max_deceleration,
                             min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, 'cruise', None

    def _follow_mode(self, ego_speed, lead_speed, distance, dt):
        """
        Follow mode: maintain safe following distance.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, 'follow', distance_error)
        """
        # Calculate desired following distance
        desired_distance = self.min_distance + self.time_headway * ego_speed

        # Distance error (positive = too far, negative = too close)
        distance_error = distance - desired_distance

        # Use distance controller to compute acceleration
        acceleration_cmd = self.distance_controller.compute(distance_error, dt)

        # Apply acceleration limits
        acceleration_cmd = max(self.max_deceleration,
                             min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, 'follow', distance_error

    def _emergency_mode(self, ego_speed, lead_speed, distance, dt):
        """
        Emergency mode: maximum braking when TTC is below threshold.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, 'emergency', distance_error)
        """
        # Calculate desired following distance for error reporting
        desired_distance = self.min_distance + self.time_headway * ego_speed
        distance_error = distance - desired_distance

        # Apply maximum deceleration
        acceleration_cmd = self.max_deceleration

        return acceleration_cmd, 'emergency', distance_error

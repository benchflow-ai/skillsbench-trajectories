"""
Adaptive Cruise Control (ACC) System

This module implements the ACC system with mode selection logic for
cruise control, following mode, and emergency braking.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with PID-based speed and distance control.

    The system operates in three modes:
    - 'cruise': Maintain set speed when no vehicle is ahead
    - 'follow': Maintain safe following distance when vehicle is detected
    - 'emergency': Emergency braking when TTC falls below threshold
    """

    def __init__(self, config):
        """
        Initialize the ACC system with configuration parameters.

        Args:
            config (dict): Configuration dictionary containing:
                - vehicle: Vehicle parameters (mass, acceleration limits)
                - acc_settings: ACC settings (set_speed, time_headway, min_distance, etc.)
                - pid_speed: PID gains for speed control
                - pid_distance: PID gains for distance control
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Initialize PID controllers
        pid_speed_config = config.get('pid_speed', {})
        pid_distance_config = config.get('pid_distance', {})

        self.speed_controller = PIDController(
            kp=pid_speed_config.get('kp', 0.1),
            ki=pid_speed_config.get('ki', 0.01),
            kd=pid_speed_config.get('kd', 0.0)
        )

        self.distance_controller = PIDController(
            kp=pid_distance_config.get('kp', 0.1),
            ki=pid_distance_config.get('ki', 0.01),
            kd=pid_distance_config.get('kd', 0.0)
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current driving scenario.

        Args:
            ego_speed (float): Current speed of the ego vehicle (m/s)
            lead_speed (float or None): Speed of lead vehicle (m/s), None if no vehicle
            distance (float or None): Distance to lead vehicle (m), None if no vehicle
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Error in following distance (m) for logging
        """
        # Determine mode based on sensor data
        mode = self._determine_mode(lead_speed, distance, ego_speed, lead_speed)

        # Compute desired distance if lead vehicle is present
        desired_distance = 0.0
        distance_error = None

        if lead_speed is not None and distance is not None:
            # Calculate desired distance based on time headway and current speed
            desired_distance = self.min_distance + (ego_speed * self.time_headway)
            # Error for distance control: negative when too close, positive when too far
            # This ensures the controller outputs deceleration when too close
            distance_error = distance - desired_distance

        # Compute acceleration command based on mode
        output_limits = (self.max_deceleration, self.max_acceleration)

        if mode == 'cruise':
            # Cruise control: maintain set speed
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt, output_limits)

        elif mode == 'follow':
            # Following mode: maintain safe distance
            speed_error = self.set_speed - ego_speed

            # Always compute speed control first
            speed_cmd = self.speed_controller.compute(speed_error, dt, output_limits)

            # Only apply distance control if it would result in more deceleration
            # This ensures we prioritize speed but maintain safety
            if distance_error is not None:
                distance_cmd = self.distance_controller.compute(distance_error, dt, output_limits)
                # Use the more conservative (lower) of the two commands
                acceleration_cmd = min(speed_cmd, distance_cmd)
            else:
                acceleration_cmd = speed_cmd

        elif mode == 'emergency':
            # Emergency mode: maximum deceleration
            acceleration_cmd = self.max_deceleration

        else:
            # Default to cruise mode
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt, output_limits)

        return acceleration_cmd, mode, distance_error

    def _determine_mode(self, lead_speed, distance, ego_speed, lead_speed_val):
        """
        Determine the operating mode based on sensor data.

        Args:
            lead_speed (float or None): Lead vehicle speed
            distance (float or None): Distance to lead vehicle
            ego_speed (float): Ego vehicle speed
            lead_speed_val (float or None): Lead vehicle speed value

        Returns:
            str: Operating mode ('cruise', 'follow', 'emergency')
        """
        # No vehicle ahead
        if lead_speed is None or distance is None:
            return 'cruise'

        # Vehicle ahead detected
        if lead_speed_val is not None:
            # Calculate Time-to-Collision (TTC)
            relative_speed = ego_speed - lead_speed_val
            ttc = float('inf')

            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

            # Emergency braking if TTC is below threshold
            if ttc < self.emergency_ttc_threshold:
                return 'emergency'

            # Following mode otherwise
            return 'follow'

        return 'cruise'

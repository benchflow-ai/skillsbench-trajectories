"""
Adaptive Cruise Control System Implementation

This module implements an ACC system with three operating modes:
- Cruise mode: Maintain set speed when no lead vehicle
- Follow mode: Maintain safe following distance
- Emergency mode: Emergency braking when collision imminent
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control System

    Automatically adjusts vehicle speed to maintain set speed or safe
    following distance based on traffic conditions.
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration parameters.

        Args:
            config (dict): Nested dictionary from vehicle_params.yaml
                          Expected structure:
                          {
                              'vehicle': {'max_acceleration', 'max_deceleration'},
                              'acc_settings': {'set_speed', 'time_headway',
                                             'min_distance', 'emergency_ttc_threshold'},
                              'pid_speed': {'kp', 'ki', 'kd'},
                              'pid_distance': {'kp', 'ki', 'kd'}
                          }
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
        self.speed_pid = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd']
        )

        self.distance_pid = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd']
        )

        # Track previous mode for mode transitions
        self.previous_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed (float): Current vehicle speed in m/s
            lead_speed (float or None): Lead vehicle speed in m/s, or None if no lead vehicle
            distance (float or None): Distance to lead vehicle in meters, or None if no lead vehicle
            dt (float): Time step in seconds

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration in m/s²
                - mode (str): Current operating mode ('cruise', 'follow', or 'emergency')
                - distance_error (float or None): Distance error in meters (None in cruise/emergency mode)
        """
        # Determine operating mode based on lead vehicle presence
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            mode = 'cruise'
            acceleration_cmd, distance_error = self._cruise_control(ego_speed, dt)

        else:
            # Lead vehicle detected - check for emergency condition
            relative_speed = ego_speed - lead_speed

            # Calculate time-to-collision (TTC)
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')  # Not approaching or invalid

            if ttc < self.emergency_ttc_threshold:
                # Emergency braking required
                mode = 'emergency'
                acceleration_cmd = self.max_deceleration
                distance_error = None

            else:
                # Normal following mode
                mode = 'follow'
                acceleration_cmd, distance_error = self._follow_control(
                    ego_speed, lead_speed, distance, dt
                )

        # Reset PID controllers when switching modes to prevent integral windup
        if mode != self.previous_mode:
            if mode == 'cruise':
                self.distance_pid.reset()
            elif mode == 'follow':
                self.speed_pid.reset()

        self.previous_mode = mode

        # Apply acceleration constraints
        acceleration_cmd = max(self.max_deceleration,
                              min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, mode, distance_error

    def _cruise_control(self, ego_speed, dt):
        """
        Speed control for cruise mode.

        Args:
            ego_speed (float): Current vehicle speed in m/s
            dt (float): Time step in seconds

        Returns:
            tuple: (acceleration_cmd, distance_error)
                - acceleration_cmd (float): Commanded acceleration
                - distance_error (None): Always None in cruise mode
        """
        # Calculate speed error
        speed_error = self.set_speed - ego_speed

        # Compute PID output
        acceleration_cmd = self.speed_pid.compute(speed_error, dt)

        return acceleration_cmd, None

    def _follow_control(self, ego_speed, lead_speed, distance, dt):
        """
        Distance control for follow mode.

        Args:
            ego_speed (float): Current vehicle speed in m/s
            lead_speed (float): Lead vehicle speed in m/s
            distance (float): Distance to lead vehicle in meters
            dt (float): Time step in seconds

        Returns:
            tuple: (acceleration_cmd, distance_error)
                - acceleration_cmd (float): Commanded acceleration
                - distance_error (float): Current distance error in meters
        """
        # Calculate desired following distance using constant time headway policy
        # desired_distance = time_headway * ego_speed + minimum_gap
        desired_distance = self.time_headway * ego_speed + self.min_distance

        # Calculate distance error (positive = too far, negative = too close)
        distance_error = distance - desired_distance

        # Compute PID output
        acceleration_cmd = self.distance_pid.compute(distance_error, dt)

        return acceleration_cmd, distance_error

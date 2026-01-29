"""
Adaptive Cruise Control System Module.

This module implements the ACC system that maintains set speed in cruise mode
and automatically adjusts speed to maintain safe following distance when
a lead vehicle is detected.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with three operating modes:

    - cruise: Maintains set speed when no lead vehicle detected
    - follow: Maintains safe following distance behind lead vehicle
    - emergency: Maximum braking when TTC < threshold

    The system uses separate PID controllers for speed and distance control.
    """

    def __init__(self, config: dict):
        """
        Initialize ACC system with configuration.

        Args:
            config: Nested dictionary containing:
                acc_settings:
                    set_speed: Target cruise speed (m/s)
                    time_headway: Time gap to maintain (seconds)
                    min_distance: Minimum gap at any speed (meters)
                    emergency_ttc_threshold: TTC threshold for emergency braking (seconds)
                vehicle:
                    max_acceleration: Maximum positive acceleration (m/s^2)
                    max_deceleration: Maximum negative acceleration (m/s^2)
                pid_speed:
                    kp, ki, kd: Speed controller gains
                pid_distance:
                    kp, ki, kd: Distance controller gains
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        speed_gains = config['pid_speed']
        self.speed_pid = PIDController(
            kp=speed_gains['kp'],
            ki=speed_gains['ki'],
            kd=speed_gains['kd']
        )

        distance_gains = config['pid_distance']
        self.distance_pid = PIDController(
            kp=distance_gains['kp'],
            ki=distance_gains['ki'],
            kd=distance_gains['kd']
        )

        # Track previous mode for controller resets
        self.prev_mode = None

    def _calculate_ttc(self, distance: float, ego_speed: float,
                       lead_speed: float) -> float:
        """
        Calculate Time-To-Collision.

        Args:
            distance: Distance to lead vehicle (m)
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)

        Returns:
            TTC in seconds, or infinity if not closing
        """
        relative_velocity = ego_speed - lead_speed

        if relative_velocity <= 0:
            return float('inf')

        return distance / relative_velocity

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """
        Calculate desired following distance based on ego speed.

        Uses the formula: d = time_headway * speed + min_distance

        Args:
            ego_speed: Current vehicle speed (m/s)

        Returns:
            Desired following distance (m)
        """
        return self.time_headway * ego_speed + self.min_distance

    def _clamp_acceleration(self, accel: float) -> float:
        """
        Clamp acceleration to vehicle limits.

        Args:
            accel: Commanded acceleration (m/s^2)

        Returns:
            Clamped acceleration within [max_decel, max_accel]
        """
        return max(self.max_decel, min(self.max_accel, accel))

    def compute(self, ego_speed: float, lead_speed: float,
                distance: float, dt: float) -> tuple:
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (m), None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
            - acceleration_cmd: Commanded acceleration (m/s^2)
            - mode: Operating mode ('cruise', 'follow', or 'emergency')
            - distance_error: Distance error in follow mode (m), None in cruise
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            mode = 'cruise'

            # Reset distance PID when switching to cruise
            if self.prev_mode != 'cruise':
                self.distance_pid.reset()

            # Speed control
            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)
            accel = self._clamp_acceleration(accel)

            self.prev_mode = mode
            return (accel, mode, None)

        # Lead vehicle detected - check for emergency
        ttc = self._calculate_ttc(distance, ego_speed, lead_speed)

        if ttc < self.emergency_ttc_threshold:
            mode = 'emergency'
            accel = self.max_decel

            self.prev_mode = mode
            return (accel, mode, 0.0)

        # Follow mode: maintain safe distance
        mode = 'follow'

        # Reset speed PID when entering follow mode
        if self.prev_mode == 'cruise':
            self.speed_pid.reset()

        # Calculate distance error
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Positive error = too far, need to accelerate
        # Negative error = too close, need to brake
        accel = self.distance_pid.compute(distance_error, dt)
        accel = self._clamp_acceleration(accel)

        self.prev_mode = mode
        return (accel, mode, distance_error)

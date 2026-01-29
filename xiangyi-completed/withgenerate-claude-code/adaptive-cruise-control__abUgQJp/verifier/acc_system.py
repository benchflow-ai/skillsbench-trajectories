"""Adaptive Cruise Control (ACC) System implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed in cruise mode
    and safe following distance when a lead vehicle is detected.

    Operating Modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': Time-to-collision below threshold, apply maximum braking

    Attributes:
        max_accel: Maximum acceleration limit (m/s^2)
        max_decel: Maximum deceleration limit (m/s^2, negative)
        set_speed: Target cruising speed (m/s)
        time_headway: Time gap to lead vehicle (seconds)
        min_gap: Minimum following distance at standstill (meters)
        emergency_ttc: TTC threshold for emergency braking (seconds)
        speed_pid: PID controller for speed control
        distance_pid: PID controller for distance control
    """

    def __init__(self, config: dict):
        """
        Initialize ACC with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - vehicle['max_acceleration']: Maximum acceleration (m/s^2)
                - vehicle['max_deceleration']: Maximum deceleration (m/s^2)
                - acc_settings['set_speed']: Target cruise speed (m/s)
                - acc_settings['time_headway']: Time headway (seconds)
                - acc_settings['min_distance']: Minimum gap (meters)
                - acc_settings['emergency_ttc_threshold']: Emergency TTC (seconds)
        """
        # Vehicle parameters
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_gap = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']

        # PID controllers (to be set externally)
        self.speed_pid = None
        self.distance_pid = None

        # Track previous mode for controller reset on transitions
        self._prev_mode = None

    def set_speed_controller(self, kp: float, ki: float, kd: float):
        """Set the speed PID controller gains with anti-windup limits."""
        self.speed_pid = PIDController(kp, ki, kd,
                                       output_min=self.max_decel,
                                       output_max=self.max_accel)

    def set_distance_controller(self, kp: float, ki: float, kd: float):
        """Set the distance PID controller gains with anti-windup limits."""
        self.distance_pid = PIDController(kp, ki, kd,
                                          output_min=self.max_decel,
                                          output_max=self.max_accel)

    def compute_desired_distance(self, ego_speed: float) -> float:
        """
        Calculate desired following distance using time headway model.

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            Desired following distance (meters)
        """
        return self.time_headway * ego_speed + self.min_gap

    def compute_ttc(self, ego_speed: float, lead_speed: float,
                    distance: float) -> float:
        """
        Calculate Time-To-Collision.

        Args:
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (meters)

        Returns:
            TTC in seconds, or float('inf') if no collision risk
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')  # No collision risk
        return distance / relative_speed

    def compute(self, ego_speed: float, lead_speed: float,
                distance: float, dt: float) -> tuple:
        """
        Compute ACC control command.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (meters), None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2), clamped to limits
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error in follow/emergency mode, None in cruise
        """
        # Cruise mode - no lead vehicle detected
        if lead_speed is None or distance is None:
            mode = 'cruise'

            # Reset distance controller on mode transition
            if self._prev_mode != 'cruise' and self.distance_pid is not None:
                self.distance_pid.reset()

            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)

            self._prev_mode = mode
            return accel, mode, None

        # Calculate TTC for emergency check
        ttc = self.compute_ttc(ego_speed, lead_speed, distance)
        desired_distance = self.compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Emergency mode - TTC below threshold
        if ttc < self.emergency_ttc:
            mode = 'emergency'

            # Reset controllers on mode transition
            if self._prev_mode != 'emergency':
                if self.speed_pid is not None:
                    self.speed_pid.reset()
                if self.distance_pid is not None:
                    self.distance_pid.reset()

            self._prev_mode = mode
            return self.max_decel, mode, distance_error

        # Follow mode - maintain safe following distance
        mode = 'follow'

        # Reset speed controller on mode transition
        if self._prev_mode != 'follow' and self.speed_pid is not None:
            self.speed_pid.reset()

        accel = self.distance_pid.compute(distance_error, dt)

        self._prev_mode = mode
        return accel, mode, distance_error

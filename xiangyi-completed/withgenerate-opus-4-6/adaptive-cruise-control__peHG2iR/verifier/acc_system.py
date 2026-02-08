"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system with cruise, follow, and emergency modes."""

    def __init__(self, config):
        """Initialize ACC with configuration.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - vehicle: mass, max_acceleration, max_deceleration
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

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

        self._prev_mode = 'cruise'

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """Compute time-to-collision.

        Returns:
            float or None: TTC in seconds, None if not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0.01 and distance > 0:
            return distance / relative_speed
        return None

    def _compute_desired_distance(self, ego_speed):
        """Compute desired following distance."""
        return self.time_headway * ego_speed + self.min_distance

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute ACC control command.

        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (m), None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: float, commanded acceleration (m/s^2)
                - mode: str, 'cruise', 'follow', or 'emergency'
                - distance_error: float or None, distance error in follow/emergency mode
        """
        # Mode selection
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)
            if ttc is not None and ttc < self.emergency_ttc:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Handle mode transitions - reset PIDs when switching
        if mode != self._prev_mode:
            if mode == 'cruise':
                self.speed_pid.reset()
            elif mode == 'follow':
                self.distance_pid.reset()
            self._prev_mode = mode

        # Compute control based on mode
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None

        elif mode == 'follow':
            desired_distance = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            accel_cmd = self.distance_pid.compute(distance_error, dt)

            # Limit speed to set_speed: don't accelerate beyond set speed
            if ego_speed >= self.set_speed and accel_cmd > 0:
                accel_cmd = 0.0

        elif mode == 'emergency':
            accel_cmd = self.max_decel
            desired_distance = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

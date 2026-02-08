"""Adaptive Cruise Control system with speed, follow, and emergency modes."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that uses PID controllers for speed and distance control.

    Modes:
        'cruise'    - No lead vehicle; maintain set speed.
        'follow'    - Lead vehicle present; maintain safe following distance.
        'emergency' - TTC below threshold; apply maximum braking.
    """

    def __init__(self, config: dict):
        """Initialize ACC from configuration dictionary.

        Args:
            config: Nested dict loaded from vehicle_params.yaml, containing
                    keys 'acc_settings', 'pid_speed', 'pid_distance', 'vehicle'.
        """
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.ttc_threshold = acc['emergency_ttc_threshold']

        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        pid_s = config['pid_speed']
        self.speed_pid = PIDController(pid_s['kp'], pid_s['ki'], pid_s['kd'])

        pid_d = config['pid_distance']
        self.distance_pid = PIDController(pid_d['kp'], pid_d['ki'], pid_d['kd'])

    def _compute_ttc(self, distance: float, ego_speed: float,
                     lead_speed: float) -> float:
        """Compute time-to-collision.

        Returns inf when vehicles are not closing.
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')
        return distance / relative_speed

    def _desired_distance(self, ego_speed: float) -> float:
        """Compute desired following distance using constant time headway."""
        return self.time_headway * ego_speed + self.min_distance

    def compute(self, ego_speed: float, lead_speed, distance,
                dt: float) -> tuple:
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s) or None if not detected.
            distance: Distance to lead vehicle (m) or None if not detected.
            dt: Time step (s).

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error).
            distance_error is None in cruise mode.
        """
        # Mode selection
        if lead_speed is None:
            mode = 'cruise'
        else:
            ttc = self._compute_ttc(distance, ego_speed, lead_speed)
            if ttc < self.ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Compute acceleration based on mode
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)
            distance_error = None
            # Reset distance PID when not in follow mode
            self.distance_pid.reset()

        elif mode == 'emergency':
            accel = self.max_decel
            desired = self._desired_distance(ego_speed)
            distance_error = distance - desired
            # Reset PIDs during emergency
            self.speed_pid.reset()
            self.distance_pid.reset()

        elif mode == 'follow':
            desired = self._desired_distance(ego_speed)
            distance_error = distance - desired
            accel = self.distance_pid.compute(distance_error, dt)
            # Reset speed PID when not in cruise
            self.speed_pid.reset()

        # Clamp acceleration to vehicle limits
        accel = max(self.max_decel, min(self.max_accel, accel))

        return accel, mode, distance_error

"""Adaptive Cruise Control system with speed and distance PID controllers."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that manages cruise, follow, and emergency modes.

    Uses two PID controllers:
    - Speed PID: maintains set_speed in cruise mode
    - Distance PID: maintains safe following distance in follow mode
    """

    def __init__(self, config):
        """Initialize ACC from configuration dict (loaded from vehicle_params.yaml).

        Args:
            config: nested dict with keys 'vehicle', 'acc_settings',
                    'pid_speed', 'pid_distance', 'simulation'
        """
        # Vehicle limits
        vehicle = config['vehicle']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        # PID controllers
        pid_s = config['pid_speed']
        self.speed_pid = PIDController(
            kp=pid_s['kp'], ki=pid_s['ki'], kd=pid_s['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

        pid_d = config['pid_distance']
        self.distance_pid = PIDController(
            kp=pid_d['kp'], ki=pid_d['ki'], kd=pid_d['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

    def _safe_following_distance(self, speed):
        """Calculate safe following distance based on current speed."""
        return speed * self.time_headway + self.min_distance

    def _time_to_collision(self, distance, ego_speed, lead_speed):
        """Calculate TTC. Returns None if not approaching."""
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: current ego vehicle speed (m/s)
            lead_speed: lead vehicle speed (m/s) or None if no lead
            distance: distance to lead vehicle (m) or None if no lead
            dt: timestep (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: float, clamped to vehicle limits
                - mode: str, one of 'cruise', 'follow', 'emergency'
                - distance_error: float or None (None in cruise mode)
        """
        # Determine mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            ttc = self._time_to_collision(distance, ego_speed, lead_speed)
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        if mode == 'cruise':
            # Speed control: track set_speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            # Reset distance PID when not following
            self.distance_pid.reset()
            distance_error = None

        elif mode == 'emergency':
            # Emergency braking: apply maximum deceleration
            accel_cmd = self.max_decel
            # Reset both PIDs during emergency
            self.speed_pid.reset()
            self.distance_pid.reset()
            distance_error = distance - self._safe_following_distance(ego_speed)

        else:  # follow
            # Distance control: maintain safe following distance
            desired_distance = self._safe_following_distance(ego_speed)
            distance_error = distance - desired_distance

            # Distance PID produces acceleration adjustment
            dist_accel = self.distance_pid.compute(distance_error, dt)

            # Also use speed PID to not exceed set_speed
            speed_error = self.set_speed - ego_speed
            speed_accel = self.speed_pid.compute(speed_error, dt)

            # Take the more conservative (lower) command
            accel_cmd = min(dist_accel, speed_accel)

        # Clamp to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

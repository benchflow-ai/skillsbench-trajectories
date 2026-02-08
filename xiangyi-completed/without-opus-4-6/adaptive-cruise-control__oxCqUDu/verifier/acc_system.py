from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with cruise, follow, and emergency modes."""

    def __init__(self, config):
        """Initialize ACC from configuration dict (loaded from vehicle_params.yaml).

        Args:
            config: Nested dict with keys 'acc_settings', 'vehicle',
                    'pid_speed', 'pid_distance'.
        """
        # Vehicle limits
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc = acc['emergency_ttc_threshold']

        # PID controllers
        sp = config['pid_speed']
        self.speed_pid = PIDController(sp['kp'], sp['ki'], sp['kd'])

        dp = config['pid_distance']
        self.distance_pid = PIDController(dp['kp'], dp['ki'], dp['kd'])

    def _desired_distance(self, ego_speed):
        """Compute desired following distance: min_distance + time_headway * speed."""
        return self.min_distance + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """Compute time-to-collision. Returns None if not closing."""
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return None
        return distance / relative_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle.
            distance: Distance to lead vehicle (m) or None.
            dt: Time step (s).

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Clamped acceleration command.
                - mode (str): 'cruise', 'follow', or 'emergency'.
                - distance_error (float or None): Distance error when following.
        """
        if lead_speed is None or distance is None:
            # Cruise mode — no lead vehicle detected
            self.distance_pid.reset()
            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)
            accel = max(self.max_decel, min(self.max_accel, accel))
            return accel, 'cruise', None

        # Lead vehicle present — check for emergency first
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        if ttc is not None and ttc < self.emergency_ttc:
            # Emergency braking
            self.speed_pid.reset()
            self.distance_pid.reset()
            accel = self.max_decel
            desired_dist = self._desired_distance(ego_speed)
            dist_error = desired_dist - distance
            return accel, 'emergency', dist_error

        # Follow mode: use distance PID to compute a speed offset,
        # then use speed PID to track the adjusted target speed.
        desired_dist = self._desired_distance(ego_speed)
        dist_error = desired_dist - distance  # positive = too close

        # Distance PID outputs a speed adjustment:
        # positive dist_error (too close) -> negative speed_adjust (slow down)
        speed_adjust = -self.distance_pid.compute(dist_error, dt)

        # Target speed = lead speed + adjustment, capped at set_speed
        target_speed = lead_speed + speed_adjust
        target_speed = max(0.0, min(target_speed, self.set_speed))

        speed_error = target_speed - ego_speed
        accel = self.speed_pid.compute(speed_error, dt)

        accel = max(self.max_decel, min(self.max_accel, accel))
        return accel, 'follow', dist_error

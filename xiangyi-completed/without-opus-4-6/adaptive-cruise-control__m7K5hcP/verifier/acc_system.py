from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control with cascade architecture.

    Outer loop: distance PID outputs a speed correction.
    Inner loop: speed PID outputs an acceleration command.
    """

    def __init__(self, config):
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        vehicle = config['vehicle']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        pid_speed_cfg = config['pid_speed']
        pid_dist_cfg = config['pid_distance']

        self.pid_speed = PIDController(
            pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd']
        )
        self.pid_distance = PIDController(
            pid_dist_cfg['kp'], pid_dist_cfg['ki'], pid_dist_cfg['kd']
        )

    def _desired_distance(self, ego_speed):
        """Compute desired following distance: min_distance + time_headway * speed."""
        return self.min_distance + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """Compute time-to-collision. Returns None if not closing."""
        closing_speed = ego_speed - lead_speed
        if closing_speed <= 0 or distance <= 0:
            return None
        return distance / closing_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s) or None if no lead.
            distance: Distance to lead vehicle (m) or None.
            dt: Time step (s).

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): clamped to [max_decel, max_accel]
                - mode (str): 'cruise', 'follow', or 'emergency'
                - distance_error (float or None): only set in follow/emergency mode
        """
        if lead_speed is None or distance is None:
            # Cruise mode — speed PID targets set_speed
            speed_error = self.set_speed - ego_speed
            raw = self.pid_speed.compute(speed_error, dt)
            accel_cmd = max(self.max_decel, min(self.max_accel, raw))

            # Anti-windup: undo integration when saturated
            if abs(raw - accel_cmd) > 0.01:
                self.pid_speed._integral -= speed_error * dt

            # Reset distance PID
            self.pid_distance.reset()
            return (accel_cmd, 'cruise', None)

        # Lead vehicle present — check emergency
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency braking
            desired_dist = self._desired_distance(ego_speed)
            dist_error = distance - desired_dist
            accel_cmd = self.max_decel
            self.pid_distance.reset()
            self.pid_speed.reset()
            return (accel_cmd, 'emergency', dist_error)

        # Follow mode — cascade control
        desired_dist = self._desired_distance(ego_speed)
        dist_error = distance - desired_dist

        # Outer loop: distance PID → speed correction
        speed_correction = self.pid_distance.compute(dist_error, dt)
        speed_correction = max(-15.0, min(15.0, speed_correction))

        # Anti-windup for distance PID
        raw_corr = self.pid_distance.kp * dist_error + \
                   self.pid_distance.ki * self.pid_distance._integral + \
                   (self.pid_distance.kd * (dist_error - self.pid_distance._prev_error) / dt
                    if self.pid_distance._prev_error is not None else 0.0)
        if abs(raw_corr) > 15.0:
            self.pid_distance._integral -= dist_error * dt

        # Target speed: lead_speed adjusted by distance correction, capped
        target_speed = lead_speed + speed_correction
        target_speed = max(0.0, min(self.set_speed, target_speed))

        # Inner loop: speed PID → acceleration
        speed_error = target_speed - ego_speed
        raw = self.pid_speed.compute(speed_error, dt)
        accel_cmd = max(self.max_decel, min(self.max_accel, raw))

        # Anti-windup for speed PID
        if abs(raw - accel_cmd) > 0.01:
            self.pid_speed._integral -= speed_error * dt

        return (accel_cmd, 'follow', dist_error)

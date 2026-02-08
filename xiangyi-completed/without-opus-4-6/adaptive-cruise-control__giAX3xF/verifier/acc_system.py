from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with cruise, follow, and emergency modes."""

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

        self.speed_pid = PIDController(
            pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd']
        )
        self.distance_pid = PIDController(
            pid_dist_cfg['kp'], pid_dist_cfg['ki'], pid_dist_cfg['kd']
        )

    def _desired_distance(self, ego_speed):
        """Compute desired following distance based on speed and time headway."""
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
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle.
            distance: Distance to lead vehicle (m), None if no lead vehicle.
            dt: Time step (s).

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration in m/s^2.
                - mode (str): 'cruise', 'follow', or 'emergency'.
                - distance_error (float or None): Distance error when following.
        """
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
            return accel_cmd, 'cruise', None

        # Lead vehicle detected - check for emergency first
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency braking
            accel_cmd = self.max_decel
            desired_dist = self._desired_distance(ego_speed)
            dist_error = distance - desired_dist
            return accel_cmd, 'emergency', dist_error

        # Follow mode
        desired_dist = self._desired_distance(ego_speed)
        dist_error = distance - desired_dist

        # Speed matching: try to match lead speed (capped at set_speed)
        target_speed = min(lead_speed, self.set_speed)
        speed_error = target_speed - ego_speed
        speed_accel = self.speed_pid.compute(speed_error, dt)

        # Distance correction: adjust based on gap error
        dist_accel = self.distance_pid.compute(dist_error, dt)

        # Combined: speed matching + distance gap correction
        accel_cmd = speed_accel + dist_accel
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, 'follow', dist_error

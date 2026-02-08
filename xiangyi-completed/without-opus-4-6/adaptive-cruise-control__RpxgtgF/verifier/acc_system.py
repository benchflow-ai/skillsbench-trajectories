"""Adaptive Cruise Control system with speed and distance control."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that switches between cruise, follow, and emergency modes."""

    def __init__(self, config):
        """Initialize the ACC system.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings.set_speed
                - acc_settings.time_headway
                - acc_settings.min_distance
                - acc_settings.emergency_ttc_threshold
                - vehicle.max_acceleration
                - vehicle.max_deceleration
                - pid_speed: dict with kp, ki, kd
                - pid_distance: dict with kp, ki, kd
        """
        acc = config['acc_settings']
        vehicle = config['vehicle']

        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        pid_speed_cfg = config['pid_speed']
        pid_dist_cfg = config['pid_distance']

        self.speed_controller = PIDController(
            kp=pid_speed_cfg['kp'],
            ki=pid_speed_cfg['ki'],
            kd=pid_speed_cfg['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel,
        )

        self.distance_controller = PIDController(
            kp=pid_dist_cfg['kp'],
            ki=pid_dist_cfg['ki'],
            kd=pid_dist_cfg['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel,
        )

    def _desired_distance(self, ego_speed):
        """Compute desired following distance based on speed.

        desired_distance = min_distance + time_headway * ego_speed
        """
        return self.min_distance + self.time_headway * ego_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), or None if no lead.
            distance: Distance to lead vehicle (m), or None if no lead.
            dt: Time step in seconds.

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration (m/s^2).
                - mode: 'cruise', 'follow', or 'emergency'.
                - distance_error: Distance error (m) or None in cruise.
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            # Reset distance controller when not in use
            self.distance_controller.reset()
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
            return (accel_cmd, 'cruise', None)

        # Check for emergency braking based on TTC
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        if ttc < self.emergency_ttc_threshold and relative_speed > 0:
            # Emergency mode: apply strong braking
            self.speed_controller.reset()
            self.distance_controller.reset()
            accel_cmd = self.max_decel
            desired_dist = self._desired_distance(ego_speed)
            distance_error = distance - desired_dist
            return (accel_cmd, 'emergency', distance_error)

        # Follow mode: maintain safe following distance
        desired_dist = self._desired_distance(ego_speed)
        distance_error = distance - desired_dist

        # Use distance PID to compute a speed correction
        # distance_error > 0: we are farther than desired (can speed up)
        # distance_error < 0: we are closer than desired (need to slow down)
        dist_correction = self.distance_controller.compute(distance_error, dt)

        # Target speed: lead vehicle speed + distance correction, capped at set_speed
        target_speed = lead_speed + dist_correction
        target_speed = max(0.0, min(target_speed, self.set_speed))

        # Use speed PID to reach target speed
        speed_error = target_speed - ego_speed
        accel_cmd = self.speed_controller.compute(speed_error, dt)

        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        return (accel_cmd, 'follow', distance_error)

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config):
        """Initialize ACC from configuration dict (loaded from vehicle_params.yaml).

        Args:
            config: Nested dict with keys 'acc_settings', 'vehicle', 'pid_speed', 'pid_distance'.
        """
        acc = config['acc_settings']
        vehicle = config['vehicle']

        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers - gains come from config (tuning_results.yaml overrides)
        pid_s = config['pid_speed']
        pid_d = config['pid_distance']
        self.speed_controller = PIDController(pid_s['kp'], pid_s['ki'], pid_s['kd'])
        self.distance_controller = PIDController(pid_d['kp'], pid_d['ki'], pid_d['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle.
            distance: Distance to lead vehicle (m), None if no lead vehicle.
            dt: Time step (s).

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2), clamped to vehicle limits.
                - mode: 'cruise', 'follow', or 'emergency'.
                - distance_error: Distance error (m) or None if cruise mode.
        """
        # No lead vehicle detected -> cruise mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            # Reset distance controller when not following
            self.distance_controller.reset()
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return (accel_cmd, mode, None)

        # Lead vehicle present - compute TTC
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0.01 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency mode
        if ttc < self.emergency_ttc_threshold and relative_speed > 0:
            mode = 'emergency'
            # Strong braking proportional to urgency
            accel_cmd = self.max_deceleration
            desired_distance = self.time_headway * ego_speed + self.min_distance
            distance_error = distance - desired_distance
            return (accel_cmd, mode, distance_error)

        # Follow mode
        mode = 'follow'
        desired_distance = self.time_headway * ego_speed + self.min_distance
        distance_error = distance - desired_distance

        # Distance control
        dist_accel = self.distance_controller.compute(distance_error, dt)

        # Speed control - target lead vehicle speed, but not exceeding set speed
        target_speed = min(lead_speed, self.set_speed)
        speed_error = target_speed - ego_speed
        speed_accel = self.speed_controller.compute(speed_error, dt)

        # Blend: use distance control primarily, with speed control as secondary
        if distance_error < -5.0:
            # Too close - prioritize distance control (braking)
            accel_cmd = min(dist_accel, speed_accel)
        elif distance_error > 10.0:
            # Far enough - allow speed to increase toward set speed
            accel_cmd = speed_accel
        else:
            # Normal following - blend both
            accel_cmd = min(dist_accel, speed_accel)

        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
        return (accel_cmd, mode, distance_error)

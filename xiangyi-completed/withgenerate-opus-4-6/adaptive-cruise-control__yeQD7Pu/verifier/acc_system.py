from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with cruise, follow, and emergency modes."""

    def __init__(self, config):
        """Initialize ACC from config dict (loaded from vehicle_params.yaml).

        Args:
            config: Nested dict with keys 'vehicle', 'acc_settings',
                    'pid_speed', 'pid_distance'.
        """
        # Vehicle parameters
        vehicle = config['vehicle']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.ttc_threshold = acc['emergency_ttc_threshold']

        # PID controllers
        sp = config['pid_speed']
        self.speed_pid = PIDController(sp['kp'], sp['ki'], sp['kd'])

        dp = config['pid_distance']
        self.distance_pid = PIDController(dp['kp'], dp['ki'], dp['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle.
            distance: Distance to lead vehicle (m), None if no lead vehicle.
            dt: Time step (s).

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error).
            distance_error is None in cruise mode.
        """
        if lead_speed is None or distance is None:
            # Cruise mode: maintain set speed
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)
            distance_error = None
            # Reset distance PID when no lead vehicle
            self.distance_pid.reset()
        else:
            # Compute TTC
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            if ttc < self.ttc_threshold:
                # Emergency mode: maximum braking
                mode = 'emergency'
                accel = self.max_decel
                desired_dist = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_dist
                # Reset PIDs during emergency
                self.speed_pid.reset()
                self.distance_pid.reset()
            else:
                # Follow mode: maintain safe following distance
                mode = 'follow'
                desired_dist = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_dist

                # Primary: distance PID for gap control
                accel = self.distance_pid.compute(distance_error, dt)

                # Soft speed limiter: bias against exceeding set speed
                # but allow it if distance error demands it
                if ego_speed > self.set_speed and distance_error >= 0:
                    speed_limit_accel = -2.0 * (ego_speed - self.set_speed)
                    accel = min(accel, speed_limit_accel)

                # Reset speed PID to avoid stale integral when returning to cruise
                self.speed_pid.reset()

        # Clamp acceleration to vehicle limits
        accel = max(self.max_decel, min(self.max_accel, accel))

        # Prevent negative speed (don't accelerate backwards)
        if ego_speed <= 0.0 and accel < 0.0:
            accel = 0.0

        return accel, mode, distance_error

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """Compute time-to-collision.

        Returns:
            TTC in seconds, or float('inf') if not approaching.
        """
        closing_speed = ego_speed - lead_speed
        if closing_speed > 0.01 and distance > 0:
            return distance / closing_speed
        return float('inf')

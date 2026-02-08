"""Adaptive Cruise Control system with speed and distance PID control."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system with cruise, follow, and emergency braking modes.

    Args:
        config: Nested dict from vehicle_params.yaml merged with tuned PID gains.
            Expected keys: 'vehicle', 'acc_settings', 'pid_speed', 'pid_distance'
    """

    def __init__(self, config):
        # Vehicle parameters
        vehicle = config['vehicle']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        # Speed PID controller
        pid_s = config['pid_speed']
        self.speed_pid = PIDController(
            kp=pid_s['kp'], ki=pid_s['ki'], kd=pid_s['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

        # Distance PID controller
        pid_d = config['pid_distance']
        self.distance_pid = PIDController(
            kp=pid_d['kp'], ki=pid_d['ki'], kd=pid_d['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

    def _safe_distance(self, ego_speed):
        """Calculate safe following distance using time headway model."""
        return ego_speed * self.time_headway + self.min_distance

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
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (m), None if no lead vehicle
            dt: Timestep (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: float, clamped to vehicle limits
                - mode: str, one of 'cruise', 'follow', 'emergency'
                - distance_error: float or None
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
            # No lead vehicle: maintain set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            # Reset distance PID so it doesn't accumulate stale integral
            self.distance_pid.reset()
            return self._clamp(accel_cmd), mode, None

        elif mode == 'emergency':
            # Emergency braking: apply maximum deceleration
            self.speed_pid.reset()
            self.distance_pid.reset()
            distance_error = distance - self._safe_distance(ego_speed)
            return self.max_decel, mode, distance_error

        else:  # follow mode
            # Maintain safe following distance
            desired_distance = self._safe_distance(ego_speed)
            distance_error = distance - desired_distance

            # Distance controller output
            dist_accel = self.distance_pid.compute(distance_error, dt)

            # Also limit speed to not exceed set_speed
            speed_error = self.set_speed - ego_speed
            speed_accel = self.speed_pid.compute(speed_error, dt)

            # Take the more conservative (lower) of the two commands
            accel_cmd = min(dist_accel, speed_accel)

            return self._clamp(accel_cmd), mode, distance_error

    def _clamp(self, accel):
        """Clamp acceleration to vehicle physical limits."""
        return max(self.max_decel, min(self.max_accel, accel))

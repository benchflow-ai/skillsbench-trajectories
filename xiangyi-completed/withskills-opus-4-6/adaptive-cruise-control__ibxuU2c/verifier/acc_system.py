"""Adaptive Cruise Control system with speed and distance PID controllers."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that manages cruise, follow, and emergency braking modes.

    In cruise mode, the speed PID tracks the set speed.
    In follow mode, the distance PID computes a target speed adjustment based on
    distance error, and the speed PID tracks that adjusted target speed.
    In emergency mode, maximum braking is applied.
    """

    def __init__(self, config):
        """Initialize ACC with configuration from vehicle_params.yaml.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        vehicle = config['vehicle']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        pid_s = config['pid_speed']
        self.speed_pid = PIDController(pid_s['kp'], pid_s['ki'], pid_s['kd'])

        pid_d = config['pid_distance']
        self.distance_pid = PIDController(pid_d['kp'], pid_d['ki'], pid_d['kd'])

        self._prev_mode = None

    def _desired_distance(self, ego_speed):
        """Calculate the desired following distance.

        desired = min_distance + time_headway * ego_speed
        """
        return self.min_distance + self.time_headway * ego_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), or None if no lead.
            distance: Distance to lead vehicle (m), or None if no lead.
            dt: Time step (s).

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                acceleration_cmd: Clamped acceleration command (m/s^2).
                mode: 'cruise', 'follow', or 'emergency'.
                distance_error: Distance error (m) or None in cruise mode.
        """
        # Determine mode
        if lead_speed is None:
            mode = 'cruise'
        else:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01 and distance is not None:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Reset PIDs on mode transition
        if mode != self._prev_mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
        self._prev_mode = mode

        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None

        elif mode == 'emergency':
            accel_cmd = self.max_decel
            desired_dist = self._desired_distance(ego_speed)
            distance_error = distance - desired_dist if distance is not None else None

        else:  # follow mode
            desired_dist = self._desired_distance(ego_speed)
            distance_error = distance - desired_dist

            # Distance PID outputs a speed adjustment
            speed_adjust = self.distance_pid.compute(distance_error, dt)

            # Target speed: lead speed + adjustment, capped at set speed
            target_speed = lead_speed + speed_adjust
            target_speed = max(0.0, min(self.set_speed, target_speed))

            # Speed PID tracks the target speed
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        # Clamp to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

"""Adaptive Cruise Control system with speed and distance PID controllers."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that maintains set speed or safe following distance.

    Modes:
        'cruise'   - No lead vehicle; maintain set_speed.
        'follow'   - Lead vehicle present; maintain safe following distance.
        'emergency' - TTC below threshold; apply maximum braking.
    """

    def __init__(self, config):
        """Initialize ACC from configuration dict (vehicle_params.yaml structure).

        Args:
            config: dict with keys 'vehicle', 'acc_settings', 'pid_speed',
                    'pid_distance', 'simulation'.
        """
        # Vehicle limits
        veh = config['vehicle']
        self.max_accel = veh['max_acceleration']
        self.max_decel = veh['max_deceleration']

        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc = acc['emergency_ttc_threshold']

        # PID controllers
        pid_s = config['pid_speed']
        self.speed_pid = PIDController(
            kp=pid_s['kp'], ki=pid_s['ki'], kd=pid_s['kd'],
            output_min=self.max_decel, output_max=self.max_accel,
        )

        pid_d = config['pid_distance']
        self.distance_pid = PIDController(
            kp=pid_d['kp'], ki=pid_d['ki'], kd=pid_d['kd'],
            output_min=self.max_decel, output_max=self.max_accel,
        )

    def _safe_distance(self, ego_speed):
        """Desired following distance = speed * time_headway + min_distance."""
        return ego_speed * self.time_headway + self.min_distance

    @staticmethod
    def _time_to_collision(distance, ego_speed, lead_speed):
        """TTC = distance / closing_speed.  None if not closing."""
        closing = ego_speed - lead_speed
        if closing <= 0 or distance <= 0:
            return None
        return distance / closing

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command for current timestep.

        Args:
            ego_speed:  current ego vehicle speed (m/s).
            lead_speed: lead vehicle speed (m/s) or None if no lead.
            distance:   gap to lead vehicle (m) or None if no lead.
            dt:         timestep (s).

        Returns:
            (acceleration_cmd, mode, distance_error)
            distance_error is None in cruise mode.
        """
        # --- Cruise mode (no lead vehicle) ---
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)
            accel = max(self.max_decel, min(self.max_accel, accel))
            return accel, 'cruise', None

        # --- Check TTC for emergency ---
        ttc = self._time_to_collision(distance, ego_speed, lead_speed)
        if ttc is not None and ttc < self.emergency_ttc:
            # Emergency braking
            self.speed_pid.reset()
            self.distance_pid.reset()
            return self.max_decel, 'emergency', None

        # --- Follow mode ---
        desired_dist = self._safe_distance(ego_speed)
        dist_error = distance - desired_dist  # positive = too far, negative = too close

        # Distance PID is the primary controller in follow mode
        dist_accel = self.distance_pid.compute(dist_error, dt)

        # Speed limiter: don't exceed set_speed
        speed_error = self.set_speed - ego_speed
        speed_accel = self.speed_pid.compute(speed_error, dt)

        # Use distance PID as primary, but cap at set_speed limit
        if ego_speed >= self.set_speed:
            # At or above set speed — use speed PID to stay at set_speed
            accel = min(dist_accel, speed_accel)
        else:
            # Below set speed — distance PID drives, speed PID limits top end
            accel = dist_accel
            if speed_accel < 0:
                # Only apply speed limit if it wants to decelerate (near set_speed)
                accel = min(accel, speed_accel)

        accel = max(self.max_decel, min(self.max_accel, accel))

        return accel, 'follow', desired_dist - distance

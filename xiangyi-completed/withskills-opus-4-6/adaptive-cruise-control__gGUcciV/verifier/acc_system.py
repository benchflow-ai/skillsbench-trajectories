"""Adaptive Cruise Control system with speed and distance PID controllers."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that manages cruise, follow, and emergency modes."""

    def __init__(self, config: dict):
        """Initialize ACC from a config dict (loaded from vehicle_params.yaml).

        Args:
            config: Nested dict with keys 'vehicle', 'acc_settings',
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
        self.speed_pid = PIDController(
            kp=sp['kp'], ki=sp['ki'], kd=sp['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

        dp = config['pid_distance']
        self.distance_pid = PIDController(
            kp=dp['kp'], ki=dp['ki'], kd=dp['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

    def _desired_distance(self, ego_speed: float) -> float:
        """Compute desired following distance based on speed."""
        return self.min_distance + self.time_headway * ego_speed

    def compute(self, ego_speed: float, lead_speed, distance,
                dt: float) -> tuple:
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), or None if no lead.
            distance: Distance to lead vehicle (m), or None if no lead.
            dt: Time step (s).

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error).
            distance_error is None in cruise mode.
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
            return (accel_cmd, 'cruise', None)

        # Compute TTC
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0.01:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency mode: TTC below threshold and closing
        if ttc < self.emergency_ttc and relative_speed > 0.01:
            accel_cmd = self.max_decel
            desired_dist = self._desired_distance(ego_speed)
            distance_error = distance - desired_dist
            return (accel_cmd, 'emergency', distance_error)

        # Follow mode: maintain safe following distance
        desired_dist = self._desired_distance(ego_speed)
        distance_error = distance - desired_dist

        # Primary: distance controller drives toward desired gap
        dist_accel = self.distance_pid.compute(distance_error, dt)

        # Secondary: speed controller ensures we don't exceed set_speed
        speed_error = self.set_speed - ego_speed
        speed_accel = self.speed_pid.compute(speed_error, dt)

        # If ego_speed > set_speed, speed controller gives negative output
        # which should override distance. Otherwise, distance controller
        # is primary.
        if ego_speed > self.set_speed:
            accel_cmd = min(dist_accel, speed_accel)
        else:
            accel_cmd = dist_accel

        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        return (accel_cmd, 'follow', distance_error)

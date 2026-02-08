"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system with cruise, follow, and emergency modes."""

    def __init__(self, config: dict):
        """Initialize ACC system from configuration dictionary.

        Args:
            config: Nested dict from vehicle_params.yaml containing
                    vehicle specs and ACC settings.
        """
        # Vehicle parameters
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_gap = config['acc_settings']['min_distance']
        self.ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # PID controllers with anti-windup
        speed_gains = config['pid_speed']
        dist_gains = config['pid_distance']
        self.speed_pid = PIDController(
            speed_gains['kp'], speed_gains['ki'], speed_gains['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )
        self.distance_pid = PIDController(
            dist_gains['kp'], dist_gains['ki'], dist_gains['kd'],
            output_min=self.max_decel, output_max=self.max_accel
        )

        self.prev_mode = None

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute safe following distance based on current speed."""
        return self.time_headway * ego_speed + self.min_gap

    def _compute_ttc(self, ego_speed: float, lead_speed: float,
                     distance: float):
        """Compute time-to-collision. Returns None if not closing."""
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            return distance / relative_speed
        return None

    def compute(self, ego_speed: float, lead_speed, distance, dt: float):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s).
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle.
            distance: Distance to lead vehicle (m), None if no lead vehicle.
            dt: Time step (s).

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error).
            distance_error is None in cruise mode.
        """
        distance_error = None

        # Mode selection
        if lead_speed is None:
            mode = 'cruise'
        else:
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)
            if ttc is not None and ttc < self.ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Reset PIDs on mode transitions
        if self.prev_mode is not None and mode != self.prev_mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
        self.prev_mode = mode

        # Compute control action
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        elif mode == 'emergency':
            accel_cmd = self.max_decel
            desired_dist = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_dist

        else:  # follow mode
            desired_dist = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_dist

            # Distance PID for gap control
            dist_accel = self.distance_pid.compute(distance_error, dt)

            # Compute desired speed: lead speed + adjustment from gap error
            # This prevents overshooting the lead vehicle
            desired_speed = min(lead_speed + dist_accel, self.set_speed)
            desired_speed = max(0.0, desired_speed)

            # Speed PID to track desired speed
            speed_error = desired_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        # Clamp to vehicle acceleration limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

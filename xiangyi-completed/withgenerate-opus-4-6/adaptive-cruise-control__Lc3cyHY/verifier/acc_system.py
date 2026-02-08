"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system with cruise, follow, and emergency modes."""

    def __init__(self, config):
        """Initialize ACC with configuration from vehicle_params.yaml.

        Args:
            config: Nested dict from vehicle_params.yaml
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle limits
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers with integral anti-windup
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd'],
            integral_limit=50.0
        )
        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd'],
            integral_limit=100.0
        )

        self.prev_mode = None

    def set_speed_gains(self, kp, ki, kd):
        """Update speed PID gains."""
        self.speed_pid = PIDController(kp, ki, kd, integral_limit=50.0)

    def set_distance_gains(self, kp, ki, kd):
        """Update distance PID gains."""
        self.distance_pid = PIDController(kp, ki, kd, integral_limit=100.0)

    def compute_ttc(self, distance, ego_speed, lead_speed):
        """Compute Time-To-Collision.

        Args:
            distance: Current gap to lead vehicle (m)
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)

        Returns:
            float: TTC in seconds, inf if not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return float('inf')
        return distance / relative_speed

    def compute_desired_distance(self, ego_speed):
        """Compute desired following distance.

        Args:
            ego_speed: Current ego speed (m/s)

        Returns:
            float: Desired distance (m)
        """
        return self.time_headway * ego_speed + self.min_distance

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead
            distance: Distance to lead vehicle (m) or None if no lead
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error in following distance (m) or None
        """
        # Mode selection
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            ttc = self.compute_ttc(distance, ego_speed, lead_speed)
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Reset PIDs on mode transition
        if mode != self.prev_mode:
            if mode == 'cruise':
                self.speed_pid.reset()
            elif mode == 'follow':
                self.distance_pid.reset()
                self.speed_pid.reset()
            self.prev_mode = mode

        # Compute control output based on mode
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None

        elif mode == 'emergency':
            accel_cmd = self.max_deceleration
            desired_dist = self.compute_desired_distance(ego_speed)
            distance_error = distance - desired_dist

        else:  # follow mode
            desired_dist = self.compute_desired_distance(ego_speed)
            distance_error = distance - desired_dist

            # Distance PID directly outputs acceleration command
            # Positive error (too far) -> accelerate
            # Negative error (too close) -> brake
            accel_cmd = self.distance_pid.compute(distance_error, dt)

            # Speed limiting: don't exceed set_speed
            if ego_speed >= self.set_speed and accel_cmd > 0:
                accel_cmd = 0.0

        # Clamp to vehicle acceleration limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, mode, distance_error

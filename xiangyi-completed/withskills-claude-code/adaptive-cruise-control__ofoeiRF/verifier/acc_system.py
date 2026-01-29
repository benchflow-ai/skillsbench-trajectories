"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with multiple operating modes."""

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml
        """
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Distance error (m) or None
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
            return (accel_cmd, 'cruise', None)

        # Calculate Time-To-Collision (TTC)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency mode: TTC below threshold
        if ttc < self.emergency_ttc_threshold:
            accel_cmd = self.max_decel
            desired_distance = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - desired_distance
            return (accel_cmd, 'emergency', distance_error)

        # Calculate desired following distance
        desired_distance = ego_speed * self.time_headway + self.min_distance
        distance_error = distance - desired_distance

        # If lead vehicle is very far (>2x desired distance) and moving faster,
        # treat it like cruise mode - just maintain set speed
        if distance > 2.0 * desired_distance and lead_speed >= ego_speed:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
            # Still report as follow mode with distance error
            return (accel_cmd, 'follow', distance_error)

        # Follow mode: actively maintain safe following distance
        # Safety check: if too close to minimum safe distance, brake hard
        safety_margin = 5.0  # m
        if distance < safety_margin:
            # Emergency braking proportional to how close we are
            brake_intensity = (safety_margin - distance) / safety_margin
            accel_cmd = self.max_decel * brake_intensity
            return (accel_cmd, 'follow', distance_error)

        # Distance PID directly controls acceleration
        # Positive error (too far) -> accelerate, Negative error (too close) -> brake
        accel_cmd = self.distance_pid.compute(distance_error, dt)

        # Also add speed matching term to follow the lead vehicle
        speed_error = lead_speed - ego_speed
        accel_cmd += self.speed_pid.compute(speed_error, dt) * 0.5

        # Apply acceleration limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return (accel_cmd, 'follow', distance_error)

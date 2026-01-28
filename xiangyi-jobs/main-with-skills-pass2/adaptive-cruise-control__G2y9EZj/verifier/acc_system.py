"""Adaptive Cruise Control System Implementation"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers
        self.speed_controller = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )
        self.distance_controller = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

        # Track previous mode to detect mode changes
        self.prev_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Control mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error (m) or None in cruise mode
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed

            # Use bang-bang control for large errors, PID for fine control
            if abs(speed_error) > 3.0:
                # Far from setpoint, use bang-bang control
                if speed_error > 0:
                    acceleration_cmd = self.max_acceleration
                else:
                    acceleration_cmd = self.max_deceleration
                # Don't completely reset, but limit integral buildup
                if abs(self.speed_controller.integral) > 5.0:
                    self.speed_controller.integral *= 0.9
            else:
                # Near setpoint, use PID control
                acceleration_cmd = self.speed_controller.compute(
                    speed_error, dt,
                    output_limits=(self.max_deceleration, self.max_acceleration)
                )

            acceleration_cmd = self._clamp_acceleration(acceleration_cmd)
            return (acceleration_cmd, 'cruise', None)

        # Calculate desired following distance
        desired_distance = self.min_distance + self.time_headway * ego_speed

        # Calculate time-to-collision (TTC)
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        # Emergency mode: collision imminent
        if ttc < self.emergency_ttc_threshold:
            # Emergency braking
            acceleration_cmd = self.max_deceleration
            distance_error = desired_distance - distance
            return (acceleration_cmd, 'emergency', distance_error)

        # Follow mode: maintain safe following distance
        distance_error = desired_distance - distance

        # Calculate relative speed
        relative_speed = ego_speed - lead_speed

        # PD control on distance error with relative speed as derivative
        # acceleration = -kp * distance_error - kd * d(distance)/dt
        # Note: d(distance)/dt = -(relative_speed)
        # So: acceleration = -kp * distance_error + kd * relative_speed

        # But we also want to account for lead vehicle acceleration
        # Assume lead accel ~ 0 for simplicity, so just use PD control

        kp_dist = self.distance_controller.kp
        kd_dist = self.distance_controller.kd
        ki_dist = self.distance_controller.ki

        # Control law: negative feedback on distance error
        # If distance_error > 0 (too close): need negative accel (brake)
        # If distance_error < 0 (too far): need positive accel (speed up)
        # Derivative term: d(distance)/dt = -relative_speed
        # If relative_speed > 0 (closing distance): brake more
        # If relative_speed < 0 (gap increasing): accelerate more
        acceleration_cmd = -kp_dist * distance_error - kd_dist * relative_speed

        # Integral term
        self.distance_controller.integral += distance_error * dt
        # Anti-windup
        if abs(self.distance_controller.integral) > 100.0:
            self.distance_controller.integral *= 0.95
        acceleration_cmd += -ki_dist * self.distance_controller.integral

        acceleration_cmd = self._clamp_acceleration(acceleration_cmd)
        return (acceleration_cmd, 'follow', distance_error)

    def _clamp_acceleration(self, acceleration):
        """Clamp acceleration to vehicle limits.

        Args:
            acceleration: Desired acceleration (m/s^2)

        Returns:
            float: Clamped acceleration within vehicle limits
        """
        return max(self.max_deceleration, min(self.max_acceleration, acceleration))

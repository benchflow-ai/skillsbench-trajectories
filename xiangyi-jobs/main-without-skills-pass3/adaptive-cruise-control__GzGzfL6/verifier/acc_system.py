"""
Adaptive Cruise Control System
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control (ACC) system that maintains set speed in cruise mode
    and adjusts speed to maintain safe following distance when a lead vehicle is detected.
    """

    def __init__(self, config: dict):
        """
        Initialize the ACC system with configuration parameters.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - vehicle: mass, max_acceleration, max_deceleration, drag_coefficient
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Initialize PID controllers
        self.speed_controller = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd']
        )
        self.distance_controller = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd']
        )

    def reset(self):
        """Reset both PID controllers."""
        self.speed_controller.reset()
        self.distance_controller.reset()

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """
        Compute the desired following distance based on time headway model.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Compute Time-To-Collision (TTC).

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or float('inf') if not approaching
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')
        return distance / relative_speed

    def compute(self, ego_speed: float, lead_speed: float, distance: float, dt: float) -> tuple:
        """
        Compute the acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s (None if no lead vehicle)
            distance: Distance to lead vehicle in meters (None if no lead vehicle)
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error in meters (None in cruise mode)
        """
        # Define output limits for anti-windup
        output_limits = (self.max_deceleration, self.max_acceleration)

        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed

            # Use proportional control with soft approach to set speed
            # Reduce gain as we approach target to avoid overshoot
            if speed_error > 0:
                # Accelerating towards set speed
                # Compute time to reach set speed at max acceleration
                time_to_target = speed_error / self.max_acceleration
                if time_to_target < 2.0:
                    # Close to target, reduce acceleration to avoid overshoot
                    scale = speed_error / (2.0 * self.max_acceleration)
                    accel_cmd = self.speed_controller.compute(speed_error, dt, output_limits)
                    accel_cmd = min(accel_cmd, self.max_acceleration * scale)
                else:
                    accel_cmd = self.speed_controller.compute(speed_error, dt, output_limits)
            else:
                # At or above set speed, use controller to decelerate
                accel_cmd = self.speed_controller.compute(speed_error, dt, output_limits)

            distance_error = None
            # Reset distance controller when transitioning to cruise
            self.distance_controller.reset()
        else:
            # Calculate TTC for safety check
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            if ttc < self.emergency_ttc_threshold:
                # Emergency mode: aggressive braking
                mode = 'emergency'
                # Apply maximum deceleration
                accel_cmd = self.max_deceleration
                desired_distance = self._compute_desired_distance(ego_speed)
                distance_error = distance - desired_distance
                # Reset controllers during emergency
                self.speed_controller.reset()
                self.distance_controller.reset()
            else:
                # Follow mode: maintain safe following distance
                mode = 'follow'
                desired_distance = self._compute_desired_distance(ego_speed)
                distance_error = distance - desired_distance

                # Primary control: match lead vehicle speed for stability
                speed_diff = lead_speed - ego_speed
                speed_match_accel = self.speed_controller.compute(speed_diff, dt, output_limits)

                # Secondary control: adjust based on distance error
                # Positive error = too far (can accelerate slightly)
                # Negative error = too close (should decelerate)
                distance_correction = self.distance_controller.compute(distance_error, dt, output_limits)

                # Combine speed matching and distance control
                # Weight depends on the magnitude of distance error
                if abs(distance_error) < 5:
                    # Close to target distance, primarily match speed
                    accel_cmd = 0.7 * speed_match_accel + 0.3 * distance_correction
                else:
                    # Large distance error, give more weight to distance control
                    accel_cmd = 0.4 * speed_match_accel + 0.6 * distance_correction

                # Safety limits based on distance error
                if distance_error < 0:  # Too close
                    # Limit acceleration more as we get closer
                    max_allowed_accel = max(self.max_deceleration,
                                           self.max_acceleration * (1 + distance_error / 10))
                    accel_cmd = min(accel_cmd, max_allowed_accel)

                if distance_error < -5:  # Significantly too close
                    # Force deceleration proportional to how close we are
                    min_decel = -0.5 * abs(distance_error)
                    accel_cmd = min(accel_cmd, min_decel)

                # Don't accelerate beyond set speed
                if ego_speed >= self.set_speed and accel_cmd > 0:
                    accel_cmd = 0.0

                # When at safe distance and matching lead speed, maintain speed (no acceleration)
                if ego_speed >= lead_speed and distance_error > 5 and accel_cmd > 0:
                    # Too far but already matching or exceeding lead - limit acceleration
                    accel_cmd = min(accel_cmd, 0.5)

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, mode, distance_error

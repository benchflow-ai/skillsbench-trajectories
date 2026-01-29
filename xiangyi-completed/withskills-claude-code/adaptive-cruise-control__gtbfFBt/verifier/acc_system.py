"""Adaptive Cruise Control system implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control.

    Modes:
        - 'cruise': Maintain set speed when no lead vehicle detected
        - 'follow': Maintain safe following distance behind lead vehicle
        - 'emergency': Emergency braking when TTC < threshold
    """

    def __init__(self, config: dict):
        """Initialize the ACC system.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        # Vehicle constraints
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers with output limits for anti-windup
        output_limits = (self.max_deceleration, self.max_acceleration)

        pid_speed = config['pid_speed']
        self.speed_controller = PIDController(
            kp=pid_speed['kp'],
            ki=pid_speed['ki'],
            kd=pid_speed['kd'],
            output_limits=output_limits
        )

        pid_distance = config['pid_distance']
        self.distance_controller = PIDController(
            kp=pid_distance['kp'],
            ki=pid_distance['ki'],
            kd=pid_distance['kd'],
            output_limits=output_limits
        )

        self._prev_mode = None

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute the desired following distance based on ego speed.

        Uses time headway model: d_desired = min_distance + time_headway * ego_speed

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Compute Time-To-Collision.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Current distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if vehicles are not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            # Not closing, TTC is infinite
            return None
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def compute(
        self,
        ego_speed: float,
        lead_speed: Optional[float],
        distance: Optional[float],
        dt: float
    ) -> Tuple[float, str, Optional[float]]:
        """Compute the acceleration command.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s, or None if no lead vehicle
            distance: Distance to lead vehicle in meters, or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration in m/s^2
            - mode: 'cruise', 'follow', or 'emergency'
            - distance_error: Distance error in meters (None for cruise mode)
        """
        # Determine mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)
            # Emergency if TTC is critically low or distance is below minimum
            if (ttc is not None and ttc < self.emergency_ttc_threshold) or distance < self.min_distance:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Reset controllers on mode change
        if mode != self._prev_mode:
            if mode == 'cruise':
                self.speed_controller.reset()
            elif mode in ('follow', 'emergency'):
                self.distance_controller.reset()
            self._prev_mode = mode

        # Compute control based on mode
        if mode == 'cruise':
            # Speed control to maintain set_speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            distance_error = None

        elif mode == 'emergency':
            # Emergency braking - apply maximum deceleration
            accel_cmd = self.max_deceleration
            desired_distance = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance

        else:  # mode == 'follow'
            # Distance control with speed limiting
            desired_distance = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance

            # Use distance controller for gap control
            # Positive error means we're too far -> accelerate
            # Negative error means we're too close -> decelerate
            accel_from_distance = self.distance_controller.compute(distance_error, dt)

            # Also consider speed difference to lead vehicle
            # If lead is faster, we can accelerate; if slower, we should slow
            speed_diff = lead_speed - ego_speed

            # Blend distance control with speed matching
            accel_cmd = accel_from_distance + 0.5 * speed_diff

            # Safety margin: stronger braking when approaching minimum distance
            safety_margin = 2.0 * self.min_distance  # Start increasing braking at 2x min distance
            if distance < safety_margin:
                # Progressive braking as we get closer to min_distance
                safety_factor = (safety_margin - distance) / (safety_margin - self.min_distance)
                safety_factor = min(1.0, max(0.0, safety_factor))
                safety_brake = safety_factor * self.max_deceleration * 0.5
                accel_cmd = min(accel_cmd, -safety_brake)

            # Don't exceed set speed even in follow mode
            if ego_speed >= self.set_speed and accel_cmd > 0:
                accel_cmd = min(accel_cmd, 0.5 * (self.set_speed - ego_speed))

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, mode, distance_error

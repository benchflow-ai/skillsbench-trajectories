"""Adaptive Cruise Control system implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config: dict):
        """Initialize the ACC system.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: ACC configuration (set_speed, time_headway, etc.)
                - vehicle: Vehicle parameters (max_acceleration, max_deceleration)
                - pid_speed: Speed PID gains
                - pid_distance: Distance PID gains
        """
        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_gap = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        # Vehicle limits
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers with output limits
        speed_gains = config['pid_speed']
        self.speed_controller = PIDController(
            kp=speed_gains['kp'],
            ki=speed_gains['ki'],
            kd=speed_gains['kd'],
            output_min=self.max_deceleration,
            output_max=self.max_acceleration
        )

        distance_gains = config['pid_distance']
        self.distance_controller = PIDController(
            kp=distance_gains['kp'],
            ki=distance_gains['ki'],
            kd=distance_gains['kd'],
            output_min=self.max_deceleration,
            output_max=self.max_acceleration
        )

        self._prev_mode = None

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute the desired following distance based on ego speed.

        Uses time headway model: desired_distance = min_gap + time_headway * ego_speed

        Args:
            ego_speed: Current speed of ego vehicle in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_gap + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Compute Time-To-Collision.

        Args:
            ego_speed: Ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if vehicles not approaching
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return None  # Not approaching or invalid distance
        return distance / relative_speed

    def compute(
        self,
        ego_speed: float,
        lead_speed: Optional[float],
        distance: Optional[float],
        dt: float
    ) -> Tuple[float, str, Optional[float]]:
        """Compute ACC control command.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s, or None if no lead vehicle
            distance: Distance to lead vehicle in meters, or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error in meters (None in cruise mode)
        """
        # No lead vehicle detected - cruise mode
        if lead_speed is None or distance is None:
            if self._prev_mode != 'cruise':
                self.distance_controller.reset()
            self._prev_mode = 'cruise'

            # Speed control to set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

            return (accel_cmd, 'cruise', None)

        # Lead vehicle detected - check for emergency
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        # Emergency condition: TTC too low OR distance below minimum safe distance
        if (ttc is not None and ttc < self.emergency_ttc_threshold) or distance < self.min_gap:
            if self._prev_mode != 'emergency':
                self.speed_controller.reset()
                self.distance_controller.reset()
            self._prev_mode = 'emergency'
            return (self.max_deceleration, 'emergency', distance - self._compute_desired_distance(ego_speed))

        # Follow mode
        if self._prev_mode == 'cruise':
            # Reset controllers when switching from cruise to follow
            self.speed_controller.reset()
            self.distance_controller.reset()
        self._prev_mode = 'follow'

        # Compute desired distance and error
        desired_distance = self._compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Two-level control: outer loop (distance) sets speed target, inner loop (speed) commands accel
        # Distance error positive means too far -> speed up
        # Distance error negative means too close -> slow down

        # Outer loop: distance controller determines speed adjustment
        speed_adjustment = self.distance_controller.compute(distance_error, dt)

        # Target speed is lead speed + adjustment, but capped by set speed
        target_speed = lead_speed + speed_adjustment
        target_speed = max(0, min(self.set_speed, target_speed))

        # Inner loop: speed control
        speed_error = target_speed - ego_speed
        accel_cmd = self.speed_controller.compute(speed_error, dt)

        return (accel_cmd, 'follow', distance_error)

"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController
from typing import Optional, Tuple


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""

    def __init__(self, config: dict):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - vehicle: mass, max_acceleration, max_deceleration
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

        # PID controllers
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

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute desired following distance based on speed and time headway.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def _compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Compute Time-To-Collision.

        Args:
            ego_speed: Ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if not approaching
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return None
        return distance / relative_speed

    def compute(
        self,
        ego_speed: float,
        lead_speed: Optional[float],
        distance: Optional[float],
        dt: float
    ) -> Tuple[float, str, Optional[float]]:
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s (None if no lead vehicle)
            distance: Distance to lead vehicle in meters (None if no lead vehicle)
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration in m/s^2
            - mode: 'cruise', 'follow', or 'emergency'
            - distance_error: Distance error in meters (None in cruise mode)
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return (accel_cmd, 'cruise', None)

        # Compute TTC for emergency detection
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        # Emergency mode: TTC below threshold
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Apply maximum braking
            return (self.max_deceleration, 'emergency', distance - self._compute_desired_distance(ego_speed))

        # Follow mode: maintain safe following distance
        desired_distance = self._compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Distance controller output (positive error = too far, need to accelerate)
        distance_accel = self.distance_controller.compute(distance_error, dt)

        # Speed controller for matching lead vehicle speed
        speed_error = lead_speed - ego_speed
        speed_accel = self.speed_controller.compute(speed_error, dt)

        # Combine controllers: use minimum to be safe
        # When far behind (positive distance_error), allow acceleration
        # When too close (negative distance_error), prioritize braking
        if distance_error < 0:
            # Too close: prioritize distance control (braking)
            accel_cmd = min(distance_accel, speed_accel)
        else:
            # Far enough: blend controls but respect set speed limit
            accel_cmd = min(distance_accel, speed_accel)
            # Don't exceed set speed in follow mode
            if ego_speed >= self.set_speed:
                speed_limit_error = self.set_speed - ego_speed
                speed_limit_accel = self.speed_controller.compute(speed_limit_error, dt)
                accel_cmd = min(accel_cmd, speed_limit_accel)

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return (accel_cmd, 'follow', distance_error)

    def reset(self):
        """Reset controller states."""
        self.speed_controller.reset()
        self.distance_controller.reset()

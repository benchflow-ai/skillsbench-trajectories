"""Adaptive Cruise Control system implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control modes."""

    def __init__(self, config: dict):
        """Initialize the ACC system with configuration.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # ACC settings
        acc_settings = config['acc_settings']
        self.set_speed = acc_settings['set_speed']
        self.time_headway = acc_settings['time_headway']
        self.min_distance = acc_settings['min_distance']
        self.emergency_ttc_threshold = acc_settings['emergency_ttc_threshold']

        # Vehicle limits
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers
        pid_speed_config = config['pid_speed']
        self.speed_controller = PIDController(
            kp=pid_speed_config['kp'],
            ki=pid_speed_config['ki'],
            kd=pid_speed_config['kd']
        )

        pid_distance_config = config['pid_distance']
        self.distance_controller = PIDController(
            kp=pid_distance_config['kp'],
            ki=pid_distance_config['ki'],
            kd=pid_distance_config['kd']
        )

    def compute_desired_distance(self, ego_speed: float) -> float:
        """Compute the desired following distance based on time headway.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Compute time-to-collision.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            Time-to-collision in seconds, or None if not approaching
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None  # Not approaching
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def compute(self, ego_speed: float, lead_speed: Optional[float],
                distance: Optional[float], dt: float) -> Tuple[float, str, Optional[float]]:
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s (None if no lead vehicle)
            distance: Distance to lead vehicle in meters (None if no lead vehicle)
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error in meters (None if cruise mode)
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return (accel_cmd, 'cruise', None)

        # Check for emergency braking condition
        ttc = self.compute_ttc(ego_speed, lead_speed, distance)
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency braking
            accel_cmd = self.max_deceleration
            desired_distance = self.compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            return (accel_cmd, 'emergency', distance_error)

        # Follow mode: maintain safe following distance
        desired_distance = self.compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Distance-based control - primary controller in follow mode
        distance_accel = self.distance_controller.compute(distance_error, dt)

        # Limit maximum speed to slightly above set_speed (allow <5% overshoot for tracking)
        max_speed = self.set_speed * 1.0499
        if ego_speed >= max_speed:
            # At max allowed speed - only allow deceleration
            if distance_accel > 0:
                accel_cmd = 0.0
            else:
                accel_cmd = distance_accel
        elif ego_speed > self.set_speed:
            # Between set_speed and max_speed - limit acceleration
            headroom = max_speed - ego_speed
            # Allow less acceleration as we approach max
            accel_limit = self.max_acceleration * (headroom / (max_speed - self.set_speed))
            if distance_accel > 0:
                accel_cmd = min(distance_accel, accel_limit)
            else:
                accel_cmd = distance_accel
        else:
            accel_cmd = distance_accel

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return (accel_cmd, 'follow', distance_error)

    def reset(self):
        """Reset both PID controllers."""
        self.speed_controller.reset()
        self.distance_controller.reset()

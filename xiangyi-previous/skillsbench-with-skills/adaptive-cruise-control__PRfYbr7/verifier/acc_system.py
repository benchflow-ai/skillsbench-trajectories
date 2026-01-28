"""Adaptive Cruise Control system implementation."""

from typing import Tuple, Optional
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control.

    Operates in three modes:
    - 'cruise': Maintain set speed when no lead vehicle is detected
    - 'follow': Maintain safe following distance when lead vehicle is present
    - 'emergency': Apply maximum braking when TTC is below threshold
    """

    def __init__(self, config: dict):
        """Initialize ACC system from configuration.

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

        # Vehicle limits
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        # PID controllers
        pid_speed_cfg = config['pid_speed']
        self.speed_controller = PIDController(
            kp=pid_speed_cfg['kp'],
            ki=pid_speed_cfg['ki'],
            kd=pid_speed_cfg['kd']
        )

        pid_dist_cfg = config['pid_distance']
        self.distance_controller = PIDController(
            kp=pid_dist_cfg['kp'],
            ki=pid_dist_cfg['ki'],
            kd=pid_dist_cfg['kd']
        )

    def compute_desired_distance(self, ego_speed: float) -> float:
        """Compute the desired following distance based on current speed.

        Uses time headway model: desired_distance = min_distance + time_headway * speed

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Compute Time-To-Collision.

        Args:
            ego_speed: Ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if vehicles are not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None  # Not closing
        if distance <= 0:
            return 0.0  # Already collided
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
            lead_speed: Lead vehicle speed in m/s, or None if no lead vehicle
            distance: Distance to lead vehicle in meters, or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2 (clamped to vehicle limits)
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error in meters (None in cruise mode)
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return (accel_cmd, 'cruise', None)

        # Check for emergency braking
        ttc = self.compute_ttc(ego_speed, lead_speed, distance)
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency mode: apply maximum braking
            return (self.max_deceleration, 'emergency', distance - self.compute_desired_distance(ego_speed))

        # Follow mode: maintain safe following distance
        desired_distance = self.compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Use distance controller for gap control
        accel_from_distance = self.distance_controller.compute(distance_error, dt)

        # Also consider speed matching with lead vehicle
        speed_error = lead_speed - ego_speed
        accel_from_speed = self.speed_controller.compute(speed_error, dt)

        # Combine: prioritize distance control, add speed matching term
        # When distance error is negative (too close), decelerate
        # When distance error is positive (too far), accelerate towards lead speed
        accel_cmd = accel_from_distance + 0.3 * accel_from_speed

        # But never exceed set speed
        if ego_speed >= self.set_speed and accel_cmd > 0:
            # At set speed, only allow deceleration or zero
            speed_to_set_error = self.set_speed - ego_speed
            accel_cmd = min(accel_cmd, self.speed_controller.compute(speed_to_set_error, dt))

        # Clamp to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return (accel_cmd, 'follow', distance_error)

    def reset(self):
        """Reset both PID controllers."""
        self.speed_controller.reset()
        self.distance_controller.reset()

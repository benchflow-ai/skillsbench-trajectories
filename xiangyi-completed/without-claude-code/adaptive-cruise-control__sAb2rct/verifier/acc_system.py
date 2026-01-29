"""Adaptive Cruise Control system implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or follows lead vehicle.

    Modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config: dict):
        """
        Initialize the ACC system.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd for speed control
                - pid_distance: kp, ki, kd for distance control
                - vehicle: max_acceleration, max_deceleration
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
        pid_distance_config = config['pid_distance']

        self.speed_controller = PIDController(
            kp=pid_speed_config['kp'],
            ki=pid_speed_config['ki'],
            kd=pid_speed_config['kd']
        )

        self.distance_controller = PIDController(
            kp=pid_distance_config['kp'],
            ki=pid_distance_config['ki'],
            kd=pid_distance_config['kd']
        )

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """
        Calculate desired following distance based on time headway and minimum gap.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """
        Calculate Time-To-Collision (TTC).

        Args:
            ego_speed: Ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if closing speed <= 0 (not approaching)
        """
        closing_speed = ego_speed - lead_speed
        if closing_speed <= 0:
            return None  # Not approaching, no collision imminent
        return distance / closing_speed

    def compute(
        self,
        ego_speed: float,
        lead_speed: Optional[float],
        distance: Optional[float],
        dt: float
    ) -> Tuple[float, str, Optional[float]]:
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s, or None if no lead vehicle
            distance: Distance to lead vehicle in meters, or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Distance error in meters, or None if in cruise mode
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            # Reset distance controller when not following
            self.distance_controller.reset()
            # Clamp acceleration
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return accel_cmd, 'cruise', None

        # Calculate TTC for emergency detection
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Emergency mode: TTC below threshold
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Apply maximum braking
            accel_cmd = self.max_deceleration
            # Reset controllers during emergency
            self.speed_controller.reset()
            self.distance_controller.reset()
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            return accel_cmd, 'emergency', distance_error

        # Follow mode: maintain safe following distance
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Distance control: positive error means we're too far, need to accelerate
        # negative error means we're too close, need to decelerate
        distance_accel = self.distance_controller.compute(distance_error, dt)

        # Also consider speed matching with lead vehicle
        speed_diff = lead_speed - ego_speed
        speed_matching_accel = self.speed_controller.compute(speed_diff, dt)

        # Combine distance and speed control
        # Weight distance control more heavily when close, speed matching when far
        if distance_error < 0:
            # Too close - prioritize distance control
            accel_cmd = distance_accel
        else:
            # At safe distance or farther - blend controls
            # But also don't exceed set speed
            if ego_speed >= self.set_speed:
                # At or above set speed, use speed control to maintain set speed
                speed_error = self.set_speed - ego_speed
                accel_cmd = self.speed_controller.compute(speed_error, dt)
            else:
                # Below set speed, blend distance and speed matching
                accel_cmd = 0.5 * distance_accel + 0.5 * speed_matching_accel

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, 'follow', distance_error

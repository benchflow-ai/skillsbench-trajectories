"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController
from typing import Optional, Tuple


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control (ACC) system that maintains set speed in cruise mode
    and adjusts speed to maintain safe following distance when a lead vehicle is detected.

    Modes:
    - 'cruise': No lead vehicle detected, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe following distance
    - 'emergency': Time-to-collision below threshold, apply emergency braking
    """

    def __init__(self, config: dict):
        """
        Initialize the ACC system with configuration.

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

        # PID controllers with reasonable integral limits
        pid_speed = config['pid_speed']
        self.speed_controller = PIDController(
            kp=pid_speed['kp'],
            ki=pid_speed['ki'],
            kd=pid_speed['kd'],
            integral_limit=5.0
        )

        pid_distance = config['pid_distance']
        self.distance_controller = PIDController(
            kp=pid_distance['kp'],
            ki=pid_distance['ki'],
            kd=pid_distance['kd'],
            integral_limit=10.0
        )

        self._prev_mode = None

    def _calculate_safe_distance(self, ego_speed: float) -> float:
        """
        Calculate the safe following distance based on current speed.

        Safe distance = min_distance + time_headway * ego_speed

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            Safe following distance (m)
        """
        return self.min_distance + self.time_headway * ego_speed

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """
        Calculate Time-to-Collision (TTC).

        TTC = distance / (ego_speed - lead_speed) when ego is faster than lead

        Args:
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            TTC in seconds, or None if not applicable (ego slower or same speed as lead)
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return None
        return distance / relative_speed

    def _clamp_acceleration(self, accel: float) -> float:
        """
        Clamp acceleration to vehicle limits.

        Args:
            accel: Requested acceleration (m/s^2)

        Returns:
            Clamped acceleration within [max_deceleration, max_acceleration]
        """
        return max(self.max_deceleration, min(self.max_acceleration, accel))

    def compute(
        self,
        ego_speed: float,
        lead_speed: Optional[float],
        distance: Optional[float],
        dt: float
    ) -> Tuple[float, str, Optional[float]]:
        """
        Compute the acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step (s)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
            - acceleration_cmd: Commanded acceleration (m/s^2)
            - mode: Operating mode ('cruise', 'follow', or 'emergency')
            - distance_error: Error in following distance (m), or None in cruise mode
        """
        # Determine mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            ttc = self._calculate_ttc(ego_speed, lead_speed, distance)
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Reset controllers on mode change
        if mode != self._prev_mode:
            self.speed_controller.reset()
            self.distance_controller.reset()
            self._prev_mode = mode

        # Compute control output based on mode
        if mode == 'cruise':
            # Maintain set speed using PID
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            distance_error = None

        elif mode == 'emergency':
            # Emergency braking - apply maximum deceleration
            accel_cmd = self.max_deceleration
            safe_distance = self._calculate_safe_distance(ego_speed)
            distance_error = distance - safe_distance

        else:  # mode == 'follow'
            # Calculate safe following distance using current ego speed
            safe_distance = self._calculate_safe_distance(ego_speed)
            distance_error = distance - safe_distance

            # Primary safety check: if actual distance is below minimum gap, brake hard
            if distance < self.min_distance:
                target_speed = max(0.0, lead_speed - 5.0)
            # Closer than safe distance - slow down proportionally
            elif distance_error < -15:
                # Significantly closer than safe - reduce speed below lead
                target_speed = lead_speed - 2.0
            elif distance_error < -5:
                # Closer than safe - slow down slightly
                target_speed = lead_speed - 0.5
            elif distance_error < 0:
                # Slightly close - nearly match lead speed
                target_speed = lead_speed
            elif distance_error > 20:
                # Lots of extra space - can accelerate to close gap
                target_speed = min(lead_speed + 3.0, self.set_speed)
            elif distance_error > 5:
                # Some extra space
                target_speed = min(lead_speed + 1.0, self.set_speed)
            else:
                # Comfortable margin - match lead speed
                target_speed = min(lead_speed, self.set_speed)

            # Ensure target speed is non-negative and doesn't exceed set speed
            target_speed = max(0.0, min(target_speed, self.set_speed))

            # Use speed controller to reach target speed
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

        # Clamp to vehicle limits
        accel_cmd = self._clamp_acceleration(accel_cmd)

        return accel_cmd, mode, distance_error

"""Adaptive Cruise Control System implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control (ACC) system that maintains set speed in cruise mode
    and adjusts speed for safe following distance when a lead vehicle is detected.

    Modes:
        - 'cruise': No lead vehicle, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config: dict):
        """
        Initialize ACC system with configuration.

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

        self._current_mode = 'cruise'
        self._prev_mode = 'cruise'

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """
        Calculate the desired following distance based on time headway and minimum gap.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return max(self.min_distance, self.time_headway * ego_speed)

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """
        Calculate Time-To-Collision.

        Args:
            ego_speed: Ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Current distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if vehicles are not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None  # Not closing
        return distance / relative_speed

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
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration in m/s^2
            - mode: Current operating mode ('cruise', 'follow', or 'emergency')
            - distance_error: Error in following distance (None in cruise mode)
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            # Reset controllers when switching to cruise from other modes
            if self._prev_mode != 'cruise':
                self.distance_controller.reset()
                self.speed_controller.reset()
            self._prev_mode = self._current_mode
            self._current_mode = 'cruise'

            # Speed control to reach set_speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

            # Clamp acceleration
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

            return accel_cmd, 'cruise', None

        # Calculate TTC for emergency detection
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Emergency mode: TTC below threshold
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            self._prev_mode = self._current_mode
            self._current_mode = 'emergency'
            # Apply maximum braking
            accel_cmd = self.max_deceleration

            # Calculate distance error for reporting
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = distance - desired_distance

            return accel_cmd, 'emergency', distance_error

        # Follow mode: maintain safe following distance
        # Reset distance controller when switching to follow mode
        if self._prev_mode != 'follow':
            self.distance_controller.reset()
        self._prev_mode = self._current_mode
        self._current_mode = 'follow'

        # Calculate desired distance and error
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Use a cascaded control approach:
        # Distance error -> desired acceleration (from distance PID)
        # Limit by speed control to prevent exceeding set_speed

        # Distance-based acceleration command
        # Positive error = too far -> speed up; Negative error = too close -> slow down
        accel_cmd = self.distance_controller.compute(distance_error, dt)

        # Speed matching: also consider matching lead vehicle speed
        # This helps smooth the response when following
        speed_diff = lead_speed - ego_speed
        accel_cmd += 0.3 * speed_diff  # Proportional speed matching

        # Limit acceleration when approaching set speed
        if ego_speed > self.set_speed - 1.0:
            # Gradually reduce max accel as we approach set speed
            max_allowed = max(0, (self.set_speed - ego_speed) * 0.5)
            accel_cmd = min(accel_cmd, max_allowed)

        # Additional safety: stronger braking if too close
        if distance < self.min_distance:
            accel_cmd = min(accel_cmd, self.max_deceleration * 0.5)

        # Clamp acceleration
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, 'follow', distance_error

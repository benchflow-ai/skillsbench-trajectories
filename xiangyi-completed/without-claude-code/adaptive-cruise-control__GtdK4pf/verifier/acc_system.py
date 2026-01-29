"""Adaptive Cruise Control System implementation."""

from typing import Optional, Tuple

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system that maintains speed or follows lead vehicle.

    Modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': TTC below threshold, apply maximum braking
    """

    def __init__(self, config: dict):
        """Initialize ACC with configuration.

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
        self.speed_pid = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd']
        )
        self.distance_pid = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd']
        )

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate desired following distance based on speed and time headway.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + self.time_headway * ego_speed

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Calculate Time To Collision.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if vehicles not closing
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
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s (None if no lead vehicle)
            distance: Distance to lead vehicle in meters (None if no lead vehicle)
            dt: Time step in seconds

        Returns:
            Tuple of:
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Current ACC mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error in following distance (None if in cruise mode)
        """
        # Cruise mode: no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            # Reset distance PID when not following
            self.distance_pid.reset()
            # Clamp to acceleration limits
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return accel_cmd, 'cruise', None

        # Calculate TTC for emergency detection
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Emergency mode: TTC below threshold
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Apply maximum braking
            self.speed_pid.reset()
            self.distance_pid.reset()
            return self.max_deceleration, 'emergency', distance - self._calculate_desired_distance(ego_speed)

        # Follow mode: maintain safe following distance
        desired_distance = self._calculate_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Use distance PID as primary control - output is acceleration command
        distance_accel = self.distance_pid.compute(distance_error, dt)

        # Combine controllers based on distance error magnitude
        if distance_error < -5.0:
            # Significantly too close - aggressive braking
            accel_cmd = self.max_deceleration
        elif distance_error < -2.0:
            # Too close - use distance control to brake
            accel_cmd = distance_accel
        elif distance_error < 2.0:
            # At desired distance - match lead speed with small distance correction
            speed_error = lead_speed - ego_speed
            speed_accel = self.speed_pid.compute(speed_error, dt)
            accel_cmd = 0.3 * distance_accel + 0.7 * speed_accel
        else:
            # Too far - use distance control to catch up
            accel_cmd = distance_accel

        # Don't exceed set speed
        if ego_speed >= self.set_speed and accel_cmd > 0:
            accel_cmd = 0.0

        # Clamp to acceleration limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, 'follow', distance_error

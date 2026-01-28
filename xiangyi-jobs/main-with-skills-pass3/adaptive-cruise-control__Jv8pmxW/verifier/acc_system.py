"""Adaptive Cruise Control System implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system that maintains set speed or safe following distance.

    Modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config: dict):
        """Initialize ACC with configuration.

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

        # Vehicle constraints
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

        self._prev_mode = 'cruise'

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate the desired following distance based on current speed.

        Args:
            ego_speed: Current ego vehicle speed in m/s

        Returns:
            Desired following distance in meters
        """
        # Distance = time_headway * speed + min_gap
        return self.time_headway * ego_speed + self.min_distance

    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Calculate Time-To-Collision.

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
        if distance <= 0:
            return 0.0  # Collision
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
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error in meters (None if in cruise mode)
        """
        # Determine mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            # Calculate TTC for emergency detection
            ttc = self._calculate_ttc(ego_speed, lead_speed, distance)
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Handle mode transitions - reset controllers when switching modes
        if mode != self._prev_mode:
            if mode == 'cruise':
                self.speed_controller.reset()
            elif mode == 'follow':
                self.distance_controller.reset()
                self.speed_controller.reset()
            self._prev_mode = mode

        # Compute acceleration based on mode
        if mode == 'cruise':
            # Speed control to maintain set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            distance_error = None

        elif mode == 'emergency':
            # Emergency braking - apply maximum deceleration
            accel_cmd = self.max_deceleration
            distance_error = self._calculate_desired_distance(ego_speed) - distance

        else:  # mode == 'follow'
            # Following mode: control speed to match lead and maintain safe distance
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = desired_distance - distance
            # Positive error = too close (actual < desired), need to brake
            # Negative error = too far (actual > desired), can accelerate

            # Calculate target speed based on lead speed and distance error
            # If too close (positive error), slow down relative to lead
            # If too far (negative error), speed up to close the gap
            # The gain on distance_error determines how aggressively we adjust speed
            distance_correction = -distance_error * 1.0  # Negative because positive error means slow down
            target_speed = lead_speed + distance_correction

            # Clamp target speed to reasonable range
            target_speed = max(0.0, min(target_speed, self.set_speed))

            # Use speed controller to track target speed
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, mode, distance_error

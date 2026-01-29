"""Adaptive Cruise Control system implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control.

    Modes:
        - 'cruise': Maintains set speed when no lead vehicle is detected
        - 'follow': Maintains safe following distance when lead vehicle is present
        - 'emergency': Emergency braking when TTC is below threshold
    """

    def __init__(self, config: dict):
        """Initialize the ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: ACC parameters (set_speed, time_headway, min_distance, emergency_ttc_threshold)
                - pid_speed: Speed PID gains (kp, ki, kd)
                - pid_distance: Distance PID gains (kp, ki, kd)
                - vehicle: Vehicle parameters (max_acceleration, max_deceleration)
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

        # PID controllers
        pid_speed_cfg = config['pid_speed']
        self.speed_controller = PIDController(
            pid_speed_cfg['kp'],
            pid_speed_cfg['ki'],
            pid_speed_cfg['kd']
        )

        pid_dist_cfg = config['pid_distance']
        self.distance_controller = PIDController(
            pid_dist_cfg['kp'],
            pid_dist_cfg['ki'],
            pid_dist_cfg['kd']
        )

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute desired following distance based on time headway.

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
            distance: Distance to lead vehicle in meters

        Returns:
            TTC in seconds, or None if vehicles are not approaching
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None  # Not approaching
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
            lead_speed: Lead vehicle speed in m/s (None if no vehicle detected)
            distance: Distance to lead vehicle in meters (None if no vehicle detected)
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error from desired distance (None if in cruise mode)
        """
        # Cruise mode - no lead vehicle detected
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            # Reset distance controller when not in use
            self.distance_controller.reset()
            # Clamp acceleration
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return accel_cmd, 'cruise', None

        # Check for emergency braking
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency braking - apply maximum deceleration
            self.speed_controller.reset()
            self.distance_controller.reset()
            desired_distance = self._compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            return self.max_deceleration, 'emergency', distance_error

        # Follow mode - maintain safe distance
        desired_distance = self._compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Use distance controller to get base acceleration
        dist_accel = self.distance_controller.compute(distance_error, dt)

        # Also consider relative speed to lead vehicle
        speed_diff = lead_speed - ego_speed

        # Combine distance and speed control
        # Positive distance_error means we have more gap than desired (can accelerate)
        # Negative distance_error means gap is too small (should decelerate)
        accel_cmd = dist_accel + 0.5 * speed_diff

        # Also limit speed to set_speed
        if ego_speed >= self.set_speed and accel_cmd > 0:
            speed_error = self.set_speed - ego_speed
            speed_accel = self.speed_controller.compute(speed_error, dt)
            accel_cmd = min(accel_cmd, speed_accel)
        else:
            # Reset speed controller when not limiting
            self.speed_controller.reset()

        # Clamp acceleration
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, 'follow', distance_error

"""Adaptive Cruise Control system implementation."""

from typing import Optional, Tuple
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system.

    Maintains set speed when no vehicle ahead, or adjusts speed to maintain
    safe following distance when a lead vehicle is detected.
    """

    def __init__(self, config: dict):
        """Initialize the ACC system.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers with anti-windup limits
        self.speed_pid = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd'],
            integral_limit=10.0  # Limit integral to prevent overshoot
        )
        self.distance_pid = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd'],
            integral_limit=20.0
        )

    def _compute_desired_distance(self, ego_speed: float) -> float:
        """Compute the desired following distance.

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
            lead_speed: Lead vehicle speed in m/s, or None if no lead vehicle
            distance: Distance to lead vehicle in m, or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error from desired distance, or None in cruise mode
        """
        # No lead vehicle detected - cruise mode
        if lead_speed is None or distance is None:
            self.distance_pid.reset()
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return accel_cmd, 'cruise', None

        # Reset speed PID when in follow mode to prevent integral buildup
        self.speed_pid.reset()

        # Compute TTC for emergency detection
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        # Compute desired distance for this speed
        desired_distance = self._compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance

        # Emergency mode - TTC below threshold OR distance critically low
        # Use 5m as absolute minimum safe distance
        min_safe_distance = 5.0
        if (ttc is not None and ttc < self.emergency_ttc_threshold) or distance < min_safe_distance:
            self.distance_pid.reset()
            return self.max_deceleration, 'emergency', distance_error

        # Follow mode - maintain safe following distance
        # Use a combined approach: distance error + relative velocity feedback

        # Distance control: PID on distance error
        distance_accel = self.distance_pid.compute(distance_error, dt)

        # Add relative velocity damping
        relative_speed = lead_speed - ego_speed  # Positive if lead is faster
        velocity_damping = 0.5 * relative_speed

        # Combine distance control and velocity damping
        accel_cmd = distance_accel + velocity_damping

        # Limit speed to set_speed
        if ego_speed >= self.set_speed:
            accel_cmd = min(accel_cmd, 0.0)
        elif ego_speed + accel_cmd * dt > self.set_speed:
            # Would exceed set speed, limit acceleration
            accel_cmd = (self.set_speed - ego_speed) / dt

        # Apply acceleration limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, 'follow', distance_error

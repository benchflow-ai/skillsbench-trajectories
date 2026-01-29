"""
Adaptive Cruise Control (ACC) System Implementation

This module implements an ACC system that maintains set speed in cruise mode
and adjusts speed to maintain safe following distance when a lead vehicle
is detected.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with three operating modes:
    - cruise: Maintain set speed when no lead vehicle present
    - follow: Maintain safe following distance when lead vehicle present
    - emergency: Apply maximum braking when TTC is critical
    """

    def __init__(self, config: dict):
        """
        Initialize ACC system with configuration.

        Args:
            config: Configuration dictionary with structure:
                - vehicle:
                    - max_acceleration: float (m/s^2)
                    - max_deceleration: float (m/s^2, negative)
                - acc_settings:
                    - set_speed: float (m/s)
                    - time_headway: float (seconds)
                    - min_distance: float (meters)
                    - emergency_ttc_threshold: float (seconds)
                - pid_speed: {kp, ki, kd}
                - pid_distance: {kp, ki, kd}
        """
        # Vehicle constraints
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']

        # Initialize PID controllers
        speed_cfg = config['pid_speed']
        self.speed_pid = PIDController(
            kp=speed_cfg['kp'],
            ki=speed_cfg['ki'],
            kd=speed_cfg['kd']
        )

        dist_cfg = config['pid_distance']
        self.distance_pid = PIDController(
            kp=dist_cfg['kp'],
            ki=dist_cfg['ki'],
            kd=dist_cfg['kd']
        )

        # Track current mode for mode transition handling
        self.current_mode = 'cruise'

    def compute(self, ego_speed: float, lead_speed: float, distance: float,
                dt: float) -> tuple:
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Clamped acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error (m) or None if in cruise mode
        """
        # Check for lead vehicle presence
        if lead_speed is None or distance is None:
            # No lead vehicle - cruise mode
            return self._cruise_mode(ego_speed, dt)

        # Calculate TTC for safety check
        ttc = self._calculate_ttc(distance, ego_speed, lead_speed)

        # Check for emergency condition
        if ttc < self.emergency_ttc:
            return self._emergency_mode()

        # Normal following mode
        return self._follow_mode(ego_speed, distance, dt)

    def _cruise_mode(self, ego_speed: float, dt: float) -> tuple:
        """Maintain set speed when no lead vehicle present."""
        # Handle mode transition
        if self.current_mode != 'cruise':
            self.distance_pid.reset()
            self.current_mode = 'cruise'

        # Speed error: positive when below set speed
        speed_error = self.set_speed - ego_speed
        accel = self.speed_pid.compute(speed_error, dt)

        return self._clamp_accel(accel), 'cruise', None

    def _follow_mode(self, ego_speed: float, distance: float,
                     dt: float) -> tuple:
        """Maintain safe following distance when lead vehicle present."""
        # Handle mode transition
        if self.current_mode != 'follow':
            self.speed_pid.reset()
            self.current_mode = 'follow'

        # Calculate target (safe) distance
        target_distance = max(self.min_distance, self.time_headway * ego_speed)

        # Distance error: positive when actual distance > target (safe)
        # negative when too close (need to slow down)
        distance_error = distance - target_distance

        accel = self.distance_pid.compute(distance_error, dt)

        # Apply speed limit: don't accelerate if already at or above set_speed
        if ego_speed >= self.set_speed and accel > 0:
            accel = min(accel, 0.0)

        return self._clamp_accel(accel), 'follow', distance_error

    def _emergency_mode(self) -> tuple:
        """Apply maximum braking when TTC is critical."""
        # Reset PIDs on emergency
        if self.current_mode != 'emergency':
            self.speed_pid.reset()
            self.distance_pid.reset()
            self.current_mode = 'emergency'

        # Apply maximum deceleration
        return self.max_decel, 'emergency', None

    def _calculate_ttc(self, distance: float, ego_speed: float,
                       lead_speed: float) -> float:
        """
        Calculate Time-To-Collision.

        Args:
            distance: Distance to lead vehicle (m)
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)

        Returns:
            TTC in seconds, or infinity if not closing
        """
        relative_speed = ego_speed - lead_speed  # Positive when closing

        if relative_speed <= 0:
            return float('inf')  # Not closing, no collision risk

        return distance / relative_speed

    def _clamp_accel(self, accel: float) -> float:
        """Clamp acceleration within vehicle limits."""
        return max(self.max_decel, min(self.max_accel, accel))

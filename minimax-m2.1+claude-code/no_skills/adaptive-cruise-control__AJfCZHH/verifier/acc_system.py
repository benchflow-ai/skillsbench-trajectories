"""
Adaptive Cruise Control (ACC) System

This module implements the ACC system with mode-based control strategies:
- Cruise mode: Maintain set speed when no lead vehicle detected
- Follow mode: Maintain safe following distance when lead vehicle detected
- Emergency mode: Maximum deceleration when TTC is critically low
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with three operating modes:
    - 'cruise': No lead vehicle, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe following distance
    - 'emergency': TTC below threshold, maximum braking
    """

    def __init__(self, config: dict):
        """
        Initialize the ACC system with configuration from vehicle_params.yaml.

        Args:
            config: Nested dictionary containing vehicle and ACC settings
        """
        # Extract ACC settings
        acc_settings = config['acc_settings']
        self.set_speed = acc_settings['set_speed']  # Target cruise speed (m/s)
        self.time_headway = acc_settings['time_headway']  # Time gap (s)
        self.min_distance = acc_settings['min_distance']  # Minimum gap (m)
        self.ttc_threshold = acc_settings['emergency_ttc_threshold']  # TTC threshold (s)

        # Extract vehicle constraints
        vehicle = config['vehicle']
        self.max_acceleration = vehicle['max_acceleration']  # m/s^2
        self.max_deceleration = vehicle['max_deceleration']  # m/s^2 (negative)

        # Extract PID gains
        pid_speed_config = config.get('pid_speed', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})
        pid_distance_config = config.get('pid_distance', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})

        # Initialize PID controllers
        self.speed_pid = PIDController(
            kp=pid_speed_config.get('kp', 0.1),
            ki=pid_speed_config.get('ki', 0.01),
            kd=pid_speed_config.get('kd', 0.0)
        )
        self.distance_pid = PIDController(
            kp=pid_distance_config.get('kp', 0.1),
            ki=pid_distance_config.get('ki', 0.01),
            kd=pid_distance_config.get('kd', 0.0)
        )

        # Current mode
        self.mode = 'cruise'

    def reset(self) -> None:
        """Reset the ACC system state."""
        self.speed_pid.reset()
        self.distance_pid.reset()
        self.mode = 'cruise'

    def _compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Compute Time To Collision (TTC).

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            Time to collision in seconds, or float('inf') if approaching stationary or negative closing rate
        """
        # Relative speed (positive means closing in)
        relative_speed = lead_speed - ego_speed

        # If lead vehicle is faster or same speed, no collision risk
        if relative_speed >= 0:
            return float('inf')

        # Time to cover distance at closing rate
        ttc = distance / abs(relative_speed)
        return ttc

    def _compute_target_distance(self, ego_speed: float, lead_speed: float = None) -> float:
        """
        Compute the target following distance based on time headway.

        Uses the slower of ego speed and set speed for conservative following.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), if available

        Returns:
            Target distance in meters
        """
        # Use the minimum of ego speed and set speed for target distance
        # This ensures we don't target a larger distance when going faster than lead
        reference_speed = min(ego_speed, self.set_speed)
        return self.min_distance + self.time_headway * reference_speed

    def compute(self, ego_speed: float, lead_speed: float, distance: float, dt: float) -> tuple:
        """
        Compute the acceleration command based on current conditions.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration (clamped to vehicle limits)
            - mode: Current operating mode ('cruise', 'follow', or 'emergency')
            - distance_error: Error in following distance (only valid in follow mode)
        """
        # Check if lead vehicle is detected
        lead_detected = lead_speed is not None and distance is not None

        if not lead_detected:
            # Cruise mode: maintain set speed
            self.mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration = self.speed_pid.compute(speed_error, dt)
            distance_error = None
        else:
            # Compute TTC for safety assessment
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            # Compute target distance
            target_distance = self._compute_target_distance(ego_speed, lead_speed)
            # Distance error: negative when too close (need to decelerate)
            distance_error = distance - target_distance

            if ttc < self.ttc_threshold:
                # Emergency mode: maximum deceleration
                self.mode = 'emergency'
                acceleration = self.max_deceleration
            else:
                # Follow mode: maintain safe following distance with speed limiting
                self.mode = 'follow'

                # Distance-based acceleration (controls spacing)
                acc_distance = self.distance_pid.compute(distance_error, dt)

                # Speed limiting: don't exceed set speed even when following
                speed_limit_acc = 0.0
                if ego_speed > self.set_speed:
                    # Need to decelerate to set speed
                    speed_error = self.set_speed - ego_speed
                    speed_limit_acc = self.speed_pid.compute(speed_error, dt)
                else:
                    speed_limit_acc = self.max_acceleration  # Can accelerate

                # In follow mode, combine both controllers:
                # - Distance controller handles spacing
                # - Speed controller limits max speed
                # Use the most conservative (minimum) acceleration
                acceleration = min(acc_distance, speed_limit_acc)

        # Clamp acceleration to vehicle limits
        acceleration = max(self.max_deceleration, min(self.max_acceleration, acceleration))

        return acceleration, self.mode, distance_error

    def update_pid_gains(self, pid_speed: dict = None, pid_distance: dict = None) -> None:
        """
        Update PID gains at runtime.

        Args:
            pid_speed: Dictionary with 'kp', 'ki', 'kd' for speed controller
            pid_distance: Dictionary with 'kp', 'ki', 'kd' for distance controller
        """
        if pid_speed:
            self.speed_pid.kp = pid_speed.get('kp', self.speed_pid.kp)
            self.speed_pid.ki = pid_speed.get('ki', self.speed_pid.ki)
            self.speed_pid.kd = pid_speed.get('kd', self.speed_pid.kd)

        if pid_distance:
            self.distance_pid.kp = pid_distance.get('kp', self.distance_pid.kp)
            self.distance_pid.ki = pid_distance.get('ki', self.distance_pid.ki)
            self.distance_pid.kd = pid_distance.get('kd', self.distance_pid.kd)

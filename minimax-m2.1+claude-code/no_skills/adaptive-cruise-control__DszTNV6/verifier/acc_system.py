"""
Adaptive Cruise Control system with PID controllers for speed and distance control.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed when no vehicles
    are detected ahead, and adjusts speed to maintain safe following distance
    when a vehicle is detected.
    """

    def __init__(self, config: dict):
        """
        Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - vehicle: vehicle parameters
                - acc_settings: ACC settings
                - pid_speed: speed controller gains
                - pid_distance: distance controller gains
                - simulation: simulation parameters
        """
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']
        self.dt = config['simulation']['dt']

        # Initialize PID controllers
        speed_pid_config = config['pid_speed']
        distance_pid_config = config['pid_distance']

        self.speed_pid = PIDController(
            kp=speed_pid_config['kp'],
            ki=speed_pid_config['ki'],
            kd=speed_pid_config['kd']
        )

        self.distance_pid = PIDController(
            kp=distance_pid_config['kp'],
            ki=distance_pid_config['ki'],
            kd=distance_pid_config['kd']
        )

    def reset(self):
        """Reset all controller states."""
        self.speed_pid.reset()
        self.distance_pid.reset()

    def compute_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> float:
        """
        Calculate Time To Collision.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            Time to collision in seconds, or float('inf') if approaching lead vehicle
        """
        # Relative speed (positive means closing in)
        relative_speed = lead_speed - ego_speed

        if distance <= 0:
            return 0.0

        if relative_speed >= 0:
            # Lead vehicle is moving away, no collision risk
            return float('inf')

        # Closing speed
        closing_speed = -relative_speed

        return distance / closing_speed

    def compute_desired_distance(self, ego_speed: float) -> float:
        """
        Calculate desired following distance based on time headway.

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            Desired following distance in meters
        """
        return self.min_distance + ego_speed * self.time_headway

    def compute(self, ego_speed: float, lead_speed: float, distance: float, dt: float) -> tuple:
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if no lead vehicle
            distance: Distance to lead vehicle in meters, None if no lead vehicle
            dt: Time step in seconds

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Acceleration command (m/s^2)
            - mode: 'cruise', 'follow', or 'emergency'
            - distance_error: Error in following distance (m), None in cruise mode
        """
        # Check if lead vehicle is detected (lead_speed is not None and distance is valid)
        lead_detected = lead_speed is not None and distance is not None and distance > 0

        if not lead_detected:
            # Cruise mode: maintain set speed
            speed_error = self.set_speed - ego_speed
            acc_cmd = self.speed_pid.compute(speed_error, dt)
            mode = 'cruise'
            distance_error = None
        else:
            # Lead vehicle detected
            ttc = self.compute_ttc(ego_speed, lead_speed, distance)

            if ttc < self.emergency_ttc_threshold:
                # Emergency mode: apply maximum deceleration
                acc_cmd = self.max_deceleration
                mode = 'emergency'
                distance_error = None
            else:
                # Follow mode: maintain safe following distance
                desired_distance = self.compute_desired_distance(ego_speed)
                distance_error = distance - desired_distance

                # Distance PID controls the speed adjustment
                speed_adjustment = self.distance_pid.compute(distance_error, dt)

                # Base speed error for cruise control
                speed_error = self.set_speed - ego_speed

                # Combine cruise control with distance-based adjustment
                acc_cmd = self.speed_pid.compute(speed_error, dt) + speed_adjustment
                mode = 'follow'

        # Apply acceleration limits
        acc_cmd = max(self.max_deceleration, min(self.max_acceleration, acc_cmd))

        return acc_cmd, mode, distance_error

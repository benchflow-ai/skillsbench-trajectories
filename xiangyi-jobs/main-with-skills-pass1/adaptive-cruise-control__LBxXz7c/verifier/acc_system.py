"""
Adaptive Cruise Control (ACC) System implementation.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that manages vehicle speed and following distance.

    Modes:
    - 'cruise': Maintain set speed when no lead vehicle
    - 'follow': Maintain safe distance when lead vehicle present
    - 'emergency': Emergency braking when TTC falls below threshold
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Dictionary with nested structure from vehicle_params.yaml
                   Must include:
                   - config['vehicle']['max_acceleration']
                   - config['vehicle']['max_deceleration']
                   - config['acc_settings']['set_speed']
                   - config['acc_settings']['time_headway']
                   - config['acc_settings']['min_distance']
                   - config['acc_settings']['emergency_ttc_threshold']
                   - config['pid_speed'] (dict with kp, ki, kd)
                   - config['pid_distance'] (dict with kp, ki, kd)
        """
        # Extract vehicle parameters
        self.max_accel = config["vehicle"]["max_acceleration"]
        self.max_decel = config["vehicle"]["max_deceleration"]

        # Extract ACC settings
        self.set_speed = config["acc_settings"]["set_speed"]
        self.time_headway = config["acc_settings"]["time_headway"]
        self.min_distance = config["acc_settings"]["min_distance"]
        self.emergency_ttc_threshold = config["acc_settings"]["emergency_ttc_threshold"]

        # Initialize PID controllers
        speed_pid = config["pid_speed"]
        distance_pid = config["pid_distance"]

        self.speed_controller = PIDController(
            speed_pid["kp"], speed_pid["ki"], speed_pid["kd"]
        )
        self.distance_controller = PIDController(
            distance_pid["kp"], distance_pid["ki"], distance_pid["kd"]
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control output.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration (m/s^2), clipped to limits
            - mode: 'cruise', 'follow', or 'emergency'
            - distance_error: Error in following distance (m) or None in cruise mode
        """
        # Determine mode and compute acceleration
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise control mode
            mode = "cruise"
            distance_error = None

            # Speed error: setpoint - current speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)

        else:
            # Lead vehicle detected
            # Calculate desired distance: min_distance + time_headway * ego_speed
            desired_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = desired_distance - distance

            # Calculate Time-To-Collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:  # Avoid division by very small numbers
                ttc = distance / relative_speed
            else:
                ttc = float("inf")

            # Check for emergency condition
            if ttc < self.emergency_ttc_threshold and relative_speed > 0:
                mode = "emergency"
                # Emergency braking at maximum deceleration
                accel_cmd = self.max_decel
            else:
                mode = "follow"
                # Use distance error to control following distance
                accel_cmd = self.distance_controller.compute(distance_error, dt)

        # Clip acceleration to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

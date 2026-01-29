"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system."""

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Dictionary containing configuration from vehicle_params.yaml
                    Expected keys: config['acc_settings'], config['vehicle']
        """
        self.config = config

        # ACC settings
        self.set_speed = config["acc_settings"]["set_speed"]
        self.time_headway = config["acc_settings"]["time_headway"]
        self.min_distance = config["acc_settings"]["min_distance"]
        self.emergency_ttc_threshold = config["acc_settings"]["emergency_ttc_threshold"]

        # Vehicle limits
        self.max_acceleration = config["vehicle"]["max_acceleration"]
        self.max_deceleration = config["vehicle"]["max_deceleration"]

        # PID controllers for speed and distance control
        speed_params = config["pid_speed"]
        distance_params = config["pid_distance"]

        self.speed_pid = PIDController(
            speed_params["kp"], speed_params["ki"], speed_params["kd"]
        )
        self.distance_pid = PIDController(
            distance_params["kp"], distance_params["ki"], distance_params["kd"]
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control command.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no vehicle ahead
            distance: Distance to lead vehicle (m) or None if no vehicle ahead
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Desired acceleration (m/s^2)
                - mode: Current control mode ('cruise', 'follow', 'emergency')
                - distance_error: Error in distance control (m)
        """

        # Determine control mode and compute command
        if lead_speed is None or distance is None:
            # No vehicle ahead - cruise control
            mode = "cruise"
            distance_error = None

            # Speed control to reach set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        else:
            # Vehicle ahead - need to control distance
            distance_error = None
            mode = None
            accel_cmd = None

            # Calculate desired distance based on time headway
            desired_distance = self.time_headway * ego_speed + self.min_distance

            # Calculate TTC (Time To Collision)
            if ego_speed > lead_speed:
                ttc = distance / (ego_speed - lead_speed)
            else:
                ttc = float("inf")

            # Check for emergency condition
            if ttc < self.emergency_ttc_threshold and ego_speed > lead_speed:
                mode = "emergency"
                # Apply maximum deceleration for safety
                accel_cmd = self.max_deceleration
            else:
                mode = "follow"

                # Distance error (positive = too close, negative = too far)
                distance_error = desired_distance - distance

                # Compute speed control and distance control
                speed_error = lead_speed - ego_speed
                speed_accel = self.speed_pid.compute(speed_error, dt)

                distance_accel = self.distance_pid.compute(distance_error, dt)

                # Combine controls with emphasis on distance
                accel_cmd = 0.4 * speed_accel + 0.6 * distance_accel

        # Apply acceleration limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

        return accel_cmd, mode, distance_error

    def reset(self):
        """Reset ACC system state."""
        self.speed_pid.reset()
        self.distance_pid.reset()

"""
Adaptive Cruise Control (ACC) system implementation.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that manages vehicle speed and maintains
    safe following distance.

    Modes:
    - 'cruise': No lead vehicle detected, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe distance
    - 'emergency': Time-to-collision below threshold, emergency braking
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config (dict): Configuration dictionary containing:
                - vehicle: vehicle specs (mass, max_acceleration, max_deceleration)
                - acc_settings: ACC parameters (set_speed, time_headway, min_distance,
                  emergency_ttc_threshold)
                - pid_speed: Speed controller gains
                - pid_distance: Distance controller gains
        """
        self.vehicle = config["vehicle"]
        self.acc_settings = config["acc_settings"]

        self.set_speed = self.acc_settings["set_speed"]
        self.time_headway = self.acc_settings["time_headway"]
        self.min_distance = self.acc_settings["min_distance"]
        self.emergency_ttc_threshold = self.acc_settings["emergency_ttc_threshold"]

        self.max_accel = self.vehicle["max_acceleration"]
        self.max_decel = self.vehicle["max_deceleration"]

        # Initialize PID controllers
        speed_gains = config["pid_speed"]
        distance_gains = config["pid_distance"]

        self.pid_speed = PIDController(speed_gains["kp"], speed_gains["ki"], speed_gains["kd"])
        self.pid_distance = PIDController(
            distance_gains["kp"], distance_gains["ki"], distance_gains["kd"]
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control command.

        Args:
            ego_speed (float): Current vehicle speed (m/s)
            lead_speed (float or None): Lead vehicle speed (m/s), None if no vehicle
            distance (float or None): Distance to lead vehicle (m), None if no vehicle
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration (-8.0 to 3.0 m/s^2)
                - mode (str): Current control mode ('cruise', 'follow', 'emergency')
                - distance_error (float): Distance error if in follow mode, None otherwise
        """
        # Determine mode
        if lead_speed is None or distance is None:
            mode = "cruise"
        else:
            # Calculate time-to-collision
            speed_diff = ego_speed - lead_speed
            if speed_diff > 0.01:  # Avoid division issues
                ttc = distance / speed_diff
            else:
                ttc = float("inf")

            # Check emergency condition
            if ttc < self.emergency_ttc_threshold and speed_diff > 0:
                mode = "emergency"
            else:
                mode = "follow"

        # Compute control command
        if mode == "cruise":
            # Maintain set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)

        elif mode == "emergency":
            # Emergency braking with maximum deceleration
            accel_cmd = self.max_decel
            distance_error = None

        else:  # follow
            # Maintain desired distance
            desired_distance = self.time_headway * lead_speed + self.min_distance
            distance_error = desired_distance - distance

            # Use distance control with fallback to speed control
            accel_from_distance = self.pid_distance.compute(distance_error, dt)

            # Also check if we need to match lead speed
            speed_error = lead_speed - ego_speed
            accel_from_speed = self.pid_speed.compute(speed_error, dt)

            # Blend: prioritize distance control when there's significant error
            if abs(distance_error) > 5.0:
                accel_cmd = accel_from_distance
            else:
                # Small distance error, focus on speed matching
                accel_cmd = accel_from_speed

        # Saturate command to limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        if mode == "cruise":
            distance_error = None

        return accel_cmd, mode, distance_error

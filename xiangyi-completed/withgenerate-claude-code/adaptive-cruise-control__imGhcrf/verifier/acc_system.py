"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or safe following distance.

    The ACC system operates in three modes:
    - Cruise: No lead vehicle detected, maintains set speed
    - Follow: Lead vehicle detected, maintains safe following distance
    - Emergency: Time-to-collision below threshold, applies maximum braking
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration parameters.

        Args:
            config (dict): Configuration dictionary containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd for speed controller
                - pid_distance: kp, ki, kd for distance controller
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle limits
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed (float): Current ego vehicle speed (m/s)
            lead_speed (float or None): Lead vehicle speed (m/s), None if no lead vehicle
            distance (float or None): Distance to lead vehicle (m), None if no lead vehicle
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration (m/s^2)
                - mode (str): Current mode ('cruise', 'follow', or 'emergency')
                - distance_error (float or None): Error from desired distance (m), None in cruise mode
        """
        # Check if lead vehicle is present
        lead_present = lead_speed is not None and distance is not None

        # Emergency mode: Check for collision risk
        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:  # Only if approaching
                ttc = distance / relative_speed
                if ttc < self.emergency_ttc_threshold:
                    # Apply maximum deceleration
                    acceleration_cmd = self.max_deceleration
                    return (acceleration_cmd, 'emergency', None)

        # Follow mode: Maintain safe following distance
        if lead_present:
            # Calculate desired following distance based on time headway
            desired_distance = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - desired_distance

            # Distance PID outputs a speed adjustment
            speed_adjustment = self.distance_pid.compute(distance_error, dt)

            # Desired speed is lead speed plus adjustment based on distance error
            desired_speed = lead_speed + speed_adjustment

            # Use speed PID to track the desired speed
            speed_error = desired_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)

            # Clamp acceleration to vehicle limits
            acceleration_cmd = max(self.max_deceleration,
                                   min(self.max_acceleration, acceleration_cmd))

            return (acceleration_cmd, 'follow', distance_error)

        # Cruise mode: Maintain set speed
        speed_error = self.set_speed - ego_speed
        acceleration_cmd = self.speed_pid.compute(speed_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration,
                               min(self.max_acceleration, acceleration_cmd))

        return (acceleration_cmd, 'cruise', None)

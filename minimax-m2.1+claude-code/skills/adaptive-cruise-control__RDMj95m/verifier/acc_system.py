"""Adaptive Cruise Control System Implementation"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control (ACC) System

    Maintains set speed when no vehicles are detected ahead.
    Automatically adjusts speed to maintain safe following distance
    when a lead vehicle is detected.
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration parameters.

        Args:
            config (dict): Configuration dictionary containing:
                - acc_settings: ACC parameters (set_speed, time_headway, min_distance, emergency_ttc_threshold)
                - pid_speed: PID gains for speed control
                - pid_distance: PID gains for distance control
                - vehicle: Vehicle parameters (max_acceleration, max_deceleration)
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers
        self.pid_speed = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute_ttc(self, ego_speed, lead_speed, distance):
        """
        Calculate Time-to-Collision (TTC).

        Args:
            ego_speed (float): Current speed of ego vehicle (m/s)
            lead_speed (float): Current speed of lead vehicle (m/s)
            distance (float): Distance to lead vehicle (m)

        Returns:
            float: Time-to-Collision in seconds (or float('inf') if no collision)
        """
        # TTC only meaningful if lead vehicle is slower or at same speed
        if lead_speed is None or lead_speed == '' or ego_speed <= lead_speed:
            return float('inf')

        # Relative speed
        relative_speed = ego_speed - lead_speed

        # Avoid division by zero
        if relative_speed <= 0:
            return float('inf')

        # Calculate TTC
        ttc = distance / relative_speed

        return ttc

    def compute_desired_distance(self, ego_speed):
        """
        Calculate desired following distance based on time headway.

        Args:
            ego_speed (float): Current speed of ego vehicle (m/s)

        Returns:
            float: Desired distance in meters
        """
        return self.time_headway * ego_speed + self.min_distance

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control output.

        Args:
            ego_speed (float): Current speed of ego vehicle (m/s)
            lead_speed (float): Current speed of lead vehicle (m/s) or None if no lead vehicle
            distance (float): Distance to lead vehicle (m) or None if no lead vehicle
            dt (float): Time step in seconds

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration (m/s^2)
                - mode (str): Control mode ('cruise', 'follow', 'emergency')
                - distance_error (float): Error in following distance (m)
        """
        # Handle empty lead_speed or distance
        if lead_speed == '' or lead_speed is None:
            lead_speed = None
        else:
            lead_speed = float(lead_speed)

        if distance == '' or distance is None:
            distance = None
        else:
            distance = float(distance)

        # Calculate TTC if lead vehicle is present
        ttc = self.compute_ttc(ego_speed, lead_speed, distance) if distance is not None else float('inf')

        # Determine control mode
        if lead_speed is None or distance is None:
            # No lead vehicle - cruise mode
            mode = 'cruise'
            distance_error = 0.0
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)

        elif ttc < self.emergency_ttc_threshold:
            # Emergency braking - TTC below threshold
            mode = 'emergency'
            distance_error = distance - self.min_distance

            # Aggressive deceleration to maintain minimum distance
            speed_error = distance - self.min_distance
            acceleration_cmd = -self.pid_distance.compute(-speed_error, dt)

            # Limit acceleration (negative for deceleration)
            acceleration_cmd = max(acceleration_cmd, self.max_deceleration)

        else:
            # Follow mode - maintain safe distance
            mode = 'follow'
            desired_distance = self.compute_desired_distance(ego_speed)
            distance_error = distance - desired_distance

            # Use distance PID for following
            acceleration_cmd = -self.pid_distance.compute(distance_error, dt)

        # Apply acceleration limits
        acceleration_cmd = max(min(acceleration_cmd, self.max_acceleration), self.max_deceleration)

        return acceleration_cmd, mode, distance_error

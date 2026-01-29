"""Adaptive Cruise Control (ACC) System Implementation"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control System

    Implements three operational modes:
    - cruise: Maintain set speed when no lead vehicle detected
    - follow: Maintain safe following distance when lead vehicle present
    - emergency: Emergency braking when TTC is critically low
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config (dict): Nested dictionary containing:
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

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers
        self.speed_controller = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_controller = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed (float): Current speed of ego vehicle (m/s)
            lead_speed (float or None): Speed of lead vehicle (m/s), None if no lead vehicle
            distance (float or None): Distance to lead vehicle (m), None if no lead vehicle
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration in m/s^2
                - mode (str): Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error (float or None): Error in following distance (m), None in cruise mode
        """
        # Cruise mode: No lead vehicle detected
        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)
            distance_error = None

        else:
            # Calculate Time-To-Collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Emergency mode: Critical TTC threshold
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                # Apply maximum deceleration
                acceleration_cmd = self.max_deceleration
                # Calculate distance error for reporting
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

            # Follow mode: Maintain safe following distance
            else:
                mode = 'follow'
                # Calculate desired following distance
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

                # Use distance controller to compute target speed adjustment
                distance_correction = self.distance_controller.compute(distance_error, dt)

                # Target speed is based on lead speed plus distance correction
                target_speed = lead_speed + distance_correction

                # Apply speed limits
                target_speed = max(0, min(target_speed, self.set_speed))

                # Use speed controller to track target speed
                speed_error = target_speed - ego_speed
                acceleration_cmd = self.speed_controller.compute(speed_error, dt)

        # Apply acceleration limits
        acceleration_cmd = max(self.max_deceleration, min(acceleration_cmd, self.max_acceleration))

        return acceleration_cmd, mode, distance_error

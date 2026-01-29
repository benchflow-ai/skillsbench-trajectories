"""
Adaptive Cruise Control System Implementation
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or follows lead vehicle.

    Modes:
    - 'cruise': No lead vehicle detected, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe following distance
    - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config (dict): Nested dictionary from vehicle_params.yaml
                          Contains 'acc_settings', 'vehicle', 'pid_speed', 'pid_distance'
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers (will be initialized with tuned parameters later)
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
            ego_speed (float): Current ego vehicle speed (m/s)
            lead_speed (float or None): Lead vehicle speed (m/s), None if no lead vehicle
            distance (float or None): Distance to lead vehicle (m), None if no lead vehicle
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration (m/s^2)
                - mode (str): Current control mode ('cruise', 'follow', 'emergency')
                - distance_error (float or None): Distance tracking error (m), None in cruise mode
        """
        # Determine mode and compute control
        if lead_speed is None or distance is None:
            # No lead vehicle - cruise mode
            mode = 'cruise'
            distance_error = None

            # Speed control: maintain set speed
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)

        else:
            # Lead vehicle present - compute TTC
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Check for emergency braking condition
            if ttc < self.emergency_ttc_threshold and relative_speed > 0:
                mode = 'emergency'
                # Apply maximum deceleration
                acceleration_cmd = self.max_deceleration

                # Calculate distance error for tracking
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance

            else:
                mode = 'follow'

                # Calculate desired following distance
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance

                # Hybrid control: combine distance error and speed matching
                # Distance control component
                distance_accel = self.distance_controller.compute(distance_error, dt)

                # Speed matching component - try to match lead vehicle speed
                speed_error = lead_speed - ego_speed
                speed_match_gain = 1.0  # Blend factor for speed matching
                speed_match_accel = speed_match_gain * speed_error

                # Combine both components
                acceleration_cmd = distance_accel + speed_match_accel

        # Apply acceleration limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, mode, distance_error

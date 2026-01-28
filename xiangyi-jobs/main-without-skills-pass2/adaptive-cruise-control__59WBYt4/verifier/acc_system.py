"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with multiple operating modes.

    Modes:
        - cruise: No lead vehicle, maintain set speed
        - follow: Lead vehicle present, maintain safe following distance
        - emergency: TTC below threshold, apply emergency braking
    """

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd for speed control
                - pid_distance: kp, ki, kd for distance control
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
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Current operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error (m) or None if in cruise mode
        """
        # Mode 1: Cruise control (no lead vehicle)
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)
            mode = 'cruise'
            distance_error = None

        else:
            # Calculate time-to-collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Mode 2: Emergency braking (TTC below threshold)
            if ttc < self.emergency_ttc_threshold:
                acceleration_cmd = self.max_deceleration
                mode = 'emergency'
                # Calculate desired distance for error reporting
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

            # Mode 3: Follow mode (maintain safe following distance)
            else:
                # Desired distance: minimum gap + time headway * ego speed
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

                # Compute desired speed based on distance error
                # If too close (negative error), slow down below lead speed
                # If too far (positive error), speed up toward lead speed
                desired_speed = lead_speed + self.distance_controller.compute(distance_error, dt)

                # Clamp desired speed to reasonable range
                desired_speed = max(0, min(self.set_speed, desired_speed))

                # Use speed controller to track desired speed
                speed_error = desired_speed - ego_speed
                acceleration_cmd = self.speed_controller.compute(speed_error, dt)

                mode = 'follow'

        # Apply acceleration limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, mode, distance_error

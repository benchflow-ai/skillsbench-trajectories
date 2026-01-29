"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system.

    Implements a hierarchical ACC controller with three modes:
    - cruise: Maintain set speed when no lead vehicle
    - follow: Follow lead vehicle at safe distance
    - emergency: Emergency braking when TTC < threshold
    """

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: ACC parameters (set_speed, time_headway, etc.)
                - vehicle: Vehicle parameters (max_acceleration, max_deceleration)
                - pid_speed: Speed controller gains
                - pid_distance: Distance controller gains
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle limits
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
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Current control mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error (m) or None in cruise mode
        """
        # Mode 1: Cruise mode (no lead vehicle)
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)
            mode = 'cruise'
            distance_error = None

        else:
            # Calculate Time-To-Collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Mode 2: Emergency braking
            if ttc < self.emergency_ttc_threshold:
                # Apply maximum deceleration
                acceleration_cmd = self.max_deceleration
                mode = 'emergency'
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance

            # Mode 3: Following mode
            else:
                # Calculate desired following distance
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance

                # Use distance controller to compute target speed
                # Target speed is lead speed adjusted by distance error
                target_speed = lead_speed + self.distance_controller.compute(distance_error, dt)

                # Clamp target speed to reasonable range
                target_speed = max(0, min(target_speed, self.set_speed))

                # Use speed controller to track target speed
                speed_error = target_speed - ego_speed
                acceleration_cmd = self.speed_controller.compute(speed_error, dt)

                mode = 'follow'

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, mode, distance_error

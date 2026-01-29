"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with multiple operating modes.

    Modes:
        - cruise: No lead vehicle detected, maintain set speed
        - follow: Lead vehicle detected, maintain safe following distance
        - emergency: Time-to-collision below threshold, emergency braking
    """

    def __init__(self, config):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
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

        # Track previous mode for controller reset
        self.prev_mode = 'cruise'

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s), None if no lead vehicle
            distance: Distance to lead vehicle (m), None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Error in following distance (m), None in cruise mode
        """
        # Mode 1: Cruise - no lead vehicle detected
        if lead_speed is None or distance is None:
            mode = 'cruise'

            # Reset distance controller when entering cruise mode
            if self.prev_mode != 'cruise':
                self.pid_distance.reset()

            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None

        else:
            # Calculate time-to-collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Mode 2: Emergency - TTC below threshold
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'

                # Reset distance controller in emergency
                if self.prev_mode != 'emergency':
                    self.pid_distance.reset()

                # Emergency braking - use maximum deceleration
                acceleration_cmd = self.max_deceleration
                # Calculate desired distance for reporting
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

            # Mode 3: Follow - maintain safe following distance
            else:
                mode = 'follow'

                # Reset distance controller when first entering follow mode
                if self.prev_mode == 'cruise':
                    self.pid_distance.reset()

                # Desired following distance: min_distance + time_headway * ego_speed
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

                # Use distance controller to compute desired speed adjustment
                acceleration_cmd = self.pid_distance.compute(distance_error, dt)

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        # Update previous mode
        self.prev_mode = mode

        return acceleration_cmd, mode, distance_error

"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with multiple operating modes.

    Modes:
    - cruise: Maintain set speed when no lead vehicle detected
    - follow: Maintain safe following distance when lead vehicle present
    - emergency: Emergency braking when TTC is below threshold
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Nested dictionary containing vehicle and ACC settings
                   Expected structure from vehicle_params.yaml:
                   - config['acc_settings']['set_speed']
                   - config['acc_settings']['time_headway']
                   - config['acc_settings']['min_distance']
                   - config['acc_settings']['emergency_ttc_threshold']
                   - config['vehicle']['max_acceleration']
                   - config['vehicle']['max_deceleration']
                   - config['pid_speed']['kp'], ['ki'], ['kd']
                   - config['pid_distance']['kp'], ['ki'], ['kd']
        """
        # Extract ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Extract vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # Initialize PID controllers
        self.speed_pid = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd']
        )

        self.distance_pid = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd']
        )

        self.current_mode = 'cruise'

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration in m/s^2
                - mode: Current operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error in meters (None in cruise mode)
        """
        # CRUISE MODE: No lead vehicle detected
        if lead_speed is None or distance is None:
            self.current_mode = 'cruise'
            distance_error = None

            # Speed control: maintain set speed
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)

            # Reset distance PID when not in use
            self.distance_pid.reset()

        else:
            # Calculate Time-to-Collision (TTC)
            relative_velocity = ego_speed - lead_speed
            if relative_velocity > 0 and distance > 0:
                ttc = distance / relative_velocity
            else:
                ttc = float('inf')

            # EMERGENCY MODE: TTC below threshold
            if ttc < self.emergency_ttc_threshold:
                self.current_mode = 'emergency'

                # Apply maximum deceleration
                acceleration_cmd = self.max_deceleration

                # Calculate desired distance for reporting
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

            # FOLLOW MODE: Maintain safe following distance
            else:
                self.current_mode = 'follow'

                # Calculate desired following distance
                desired_distance = self.min_distance + self.time_headway * ego_speed

                # Distance error
                distance_error = distance - desired_distance

                # Use distance PID to control following
                acceleration_cmd = self.distance_pid.compute(distance_error, dt)

                # Reset speed PID when not in use
                self.speed_pid.reset()

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, self.current_mode, distance_error

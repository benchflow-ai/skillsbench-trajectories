"""
Adaptive Cruise Control (ACC) system implementation.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system with speed and distance control.
    """

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle limits
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers (will be initialized with tuned gains later)
        speed_pid = config.get('pid_speed', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})
        distance_pid = config.get('pid_distance', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})

        self.speed_controller = PIDController(
            speed_pid['kp'],
            speed_pid['ki'],
            speed_pid['kd']
        )
        self.distance_controller = PIDController(
            distance_pid['kp'],
            distance_pid['ki'],
            distance_pid['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error in following distance (m) or None
        """
        # No lead vehicle - cruise control mode
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

            # Emergency braking mode
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                # Emergency braking - apply maximum deceleration
                acceleration_cmd = self.max_deceleration
                # Calculate desired following distance
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

            # Follow mode
            else:
                mode = 'follow'
                # Calculate desired following distance
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

                # Use distance-based control
                # Directly compute acceleration from distance error
                acceleration_cmd = self.distance_controller.compute(distance_error, dt)

                # Add speed matching term to track lead vehicle speed
                speed_error = lead_speed - ego_speed
                speed_correction = self.speed_controller.compute(speed_error, dt)

                # Combine distance and speed control
                # Distance control dominates when far from desired distance
                # Speed matching dominates when near desired distance
                weight_distance = min(1.0, abs(distance_error) / 10.0)
                weight_speed = 1.0 - weight_distance
                acceleration_cmd = weight_distance * acceleration_cmd + weight_speed * speed_correction

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, mode, distance_error

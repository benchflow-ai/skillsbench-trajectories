"""
Adaptive Cruise Control (ACC) system implementation.
Manages speed control, distance regulation, and safety features.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed in cruise mode
    and adjusts speed to maintain safe following distance in follow mode.
    """

    def __init__(self, config):
        """
        Initialize the ACC system with configuration parameters.

        Args:
            config (dict): Configuration dictionary with nested structure:
                - config['vehicle']: Vehicle parameters (mass, acceleration limits)
                - config['acc_settings']: ACC settings (set_speed, time_headway, etc.)
                - config['pid_speed']: Speed PID gains (kp, ki, kd)
                - config['pid_distance']: Distance PID gains (kp, ki, kd)
                - config['simulation']: Simulation parameters (dt)
        """
        self.config = config

        # Vehicle parameters
        vehicle = config['vehicle']
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        # ACC settings
        acc = config['acc_settings']
        self.set_speed = acc['set_speed']
        self.time_headway = acc['time_headway']
        self.min_distance = acc['min_distance']
        self.emergency_ttc_threshold = acc['emergency_ttc_threshold']

        # Initialize PID controllers
        speed_pid = config['pid_speed']
        self.speed_controller = PIDController(
            kp=speed_pid['kp'],
            ki=speed_pid['ki'],
            kd=speed_pid['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel
        )

        distance_pid = config['pid_distance']
        self.distance_controller = PIDController(
            kp=distance_pid['kp'],
            ki=distance_pid['ki'],
            kd=distance_pid['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed (float): Current vehicle speed (m/s)
            lead_speed (float or None): Speed of lead vehicle (m/s), None if no vehicle ahead
            distance (float or None): Distance to lead vehicle (m), None if no vehicle ahead
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Commanded acceleration (m/s^2)
                - mode (str): Operating mode ('cruise', 'follow', 'emergency')
                - distance_error (float): Distance error in follow mode, None in cruise mode
        """
        # Mode 1: Cruise control (no vehicle ahead)
        if lead_speed is None or distance is None:
            # Speed error: setpoint - measured
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            return accel_cmd, 'cruise', None

        # Calculate desired distance: min_distance + time_headway * ego_speed
        desired_distance = self.min_distance + self.time_headway * ego_speed

        # Calculate Time-To-Collision (TTC)
        # TTC = distance / (ego_speed - lead_speed) if ego is faster
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0.1:  # ego vehicle approaching
            ttc = distance / relative_speed
        else:
            ttc = float('inf')  # safe if not approaching

        # Mode 3: Emergency braking
        if ttc < self.emergency_ttc_threshold:
            accel_cmd = self.max_decel  # Emergency brake
            distance_error = distance - desired_distance
            return accel_cmd, 'emergency', distance_error

        # Mode 2: Following (maintain safe distance)
        distance_error = distance - desired_distance

        # Use distance control if following, but also respect speed limits
        accel_from_distance = self.distance_controller.compute(distance_error, dt)

        # Speed control: don't exceed set speed
        speed_error = self.set_speed - ego_speed
        accel_from_speed = self.speed_controller.compute(speed_error, dt)

        # Use more conservative (lower) acceleration between the two controllers
        if accel_from_distance < accel_from_speed:
            accel_cmd = accel_from_distance
        else:
            accel_cmd = accel_from_speed

        return accel_cmd, 'follow', distance_error

    def reset(self):
        """Reset all internal states."""
        self.speed_controller.reset()
        self.distance_controller.reset()

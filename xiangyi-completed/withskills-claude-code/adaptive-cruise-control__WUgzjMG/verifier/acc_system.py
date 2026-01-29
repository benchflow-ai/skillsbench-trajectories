"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    ACC system that maintains set speed or safe following distance.

    Modes:
    - 'cruise': No lead vehicle, maintain set speed
    - 'follow': Lead vehicle present, maintain safe distance
    - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config (dict): Configuration dict with acc_settings and pid gains
        """
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Speed PID controller
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        # Distance PID controller
        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

        # Acceleration limits
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on ACC logic.

        Args:
            ego_speed (float): Current ego vehicle speed (m/s)
            lead_speed (float or None): Lead vehicle speed (m/s), None if no vehicle ahead
            distance (float or None): Distance to lead vehicle (m), None if no vehicle ahead
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Command acceleration in m/s^2
                - mode (str): Current ACC mode ('cruise', 'follow', or 'emergency')
                - distance_error (float or None): Distance error (desired - actual)
        """
        # Determine mode and calculate acceleration command
        if lead_speed is None or distance is None:
            # No lead vehicle - cruise mode
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None
        else:
            # Lead vehicle detected
            # Calculate desired distance based on time headway and current speed
            desired_distance = max(
                self.min_distance,
                self.time_headway * ego_speed
            )

            # Check for emergency condition (TTC < threshold)
            speed_diff = ego_speed - lead_speed
            if speed_diff > 0.1:  # Only calculate TTC if approaching
                ttc = distance / speed_diff
            else:
                ttc = float('inf')

            if ttc < self.emergency_ttc_threshold:
                # Emergency braking
                mode = 'emergency'
                accel_cmd = self.max_decel
                distance_error = desired_distance - distance
            else:
                # Follow mode - maintain safe distance
                mode = 'follow'
                distance_error = desired_distance - distance

                # Use distance PID to control following
                distance_accel = self.distance_pid.compute(distance_error, dt)

                # Also consider speed error to maintain efficiency
                speed_error = lead_speed - ego_speed
                speed_accel = self.speed_pid.compute(speed_error, dt)

                # Blend: distance control is primary, speed is secondary
                accel_cmd = 0.7 * distance_accel + 0.3 * speed_accel

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

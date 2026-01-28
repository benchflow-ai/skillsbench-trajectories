"""
Adaptive Cruise Control (ACC) system implementation.

Manages multiple control modes (cruise, follow, emergency) and uses
PID controllers for speed and distance regulation.
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    ACC system that maintains speed or safe following distance.

    Modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe distance
        - 'emergency': TTC below threshold, apply emergency braking
    """

    def __init__(self, config):
        """
        Initialize ACC system from configuration.

        Args:
            config (dict): Configuration dict with structure:
                {
                    'acc_settings': {
                        'set_speed': float,
                        'time_headway': float,
                        'min_distance': float,
                        'emergency_ttc_threshold': float
                    },
                    'vehicle': {
                        'max_acceleration': float,
                        'max_deceleration': float
                    },
                    'pid_speed': {'kp': float, 'ki': float, 'kd': float},
                    'pid_distance': {'kp': float, 'ki': float, 'kd': float}
                }
        """
        self.config = config

        # Extract settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle dynamics
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # PID controllers
        pid_speed_cfg = config['pid_speed']
        pid_dist_cfg = config['pid_distance']

        self.pid_speed = PIDController(
            kp=pid_speed_cfg['kp'],
            ki=pid_speed_cfg['ki'],
            kd=pid_speed_cfg['kd'],
            max_output=self.max_accel,
            min_output=self.max_decel
        )

        self.pid_distance = PIDController(
            kp=pid_dist_cfg['kp'],
            ki=pid_dist_cfg['ki'],
            kd=pid_dist_cfg['kd'],
            max_output=self.max_accel,
            min_output=self.max_decel
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command for current state.

        Args:
            ego_speed (float): Current ego vehicle speed (m/s)
            lead_speed (float or None): Lead vehicle speed or None if not present
            distance (float or None): Distance to lead vehicle or None if not present
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Target acceleration (m/s^2)
                - mode (str): Current control mode
                - distance_error (float or None): Distance tracking error
        """
        # Determine mode and compute control
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None

        else:
            # Lead vehicle detected
            # Calculate desired distance using time headway with lead vehicle speed
            # d_desired = v_lead * t_h + d_min
            desired_distance = lead_speed * self.time_headway + self.min_distance

            # Calculate Time-To-Collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Check for emergency condition
            if ttc < self.emergency_ttc_threshold and ego_speed > lead_speed:
                mode = 'emergency'
                # Emergency braking - apply maximum deceleration
                accel_cmd = self.max_decel
                distance_error = distance - desired_distance

            else:
                mode = 'follow'
                # Distance control using PID
                distance_error = distance - desired_distance
                accel_cmd = self.pid_distance.compute(distance_error, dt)

        # Saturate acceleration command
        accel_cmd = max(min(accel_cmd, self.max_accel), self.max_decel)

        return accel_cmd, mode, distance_error

    def reset(self):
        """Reset all internal PID controller states."""
        self.pid_speed.reset()
        self.pid_distance.reset()

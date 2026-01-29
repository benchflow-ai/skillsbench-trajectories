"""Adaptive Cruise Control System."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with multi-mode operation."""

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Dictionary with configuration from vehicle_params.yaml
                Expected structure:
                {
                    'vehicle': {...},
                    'acc_settings': {...},
                    'pid_speed': {'kp': ..., 'ki': ..., 'kd': ...},
                    'pid_distance': {'kp': ..., 'ki': ..., 'kd': ...}
                }
        """
        # Vehicle parameters
        self.mass = config['vehicle']['mass']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # PID controllers
        pid_speed_cfg = config['pid_speed']
        pid_dist_cfg = config['pid_distance']
        self.pid_speed = PIDController(pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd'])
        self.pid_distance = PIDController(
            pid_dist_cfg['kp'], pid_dist_cfg['ki'], pid_dist_cfg['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC acceleration command.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)

        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Acceleration command (m/s^2)
            - mode: Operating mode ('cruise', 'follow', or 'emergency')
            - distance_error: Distance error (m) or None
        """
        # Determine operating mode
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None
        else:
            # Lead vehicle detected - check for emergency condition
            if ego_speed > 0.001:  # Avoid division by zero
                ttc = distance / ego_speed
            else:
                ttc = float('inf')

            if ttc < self.emergency_ttc_threshold:
                # Emergency braking
                mode = 'emergency'
                accel_cmd = self.max_decel
                distance_error = distance - self.min_distance
            else:
                # Follow mode - maintain safe distance
                mode = 'follow'

                # Calculate desired speed based on distance and time headway
                # Desired distance = time_headway * lead_speed + min_distance
                desired_distance = self.time_headway * lead_speed + self.min_distance
                distance_error = distance - desired_distance

                # Use distance error to compute acceleration
                dist_accel = self.pid_distance.compute(distance_error, dt)

                # Also use speed error for smooth control
                speed_error = self.set_speed - ego_speed
                speed_accel = self.pid_speed.compute(speed_error, dt)

                # Combine distance control (priority) and speed control
                accel_cmd = dist_accel * 0.7 + speed_accel * 0.3

        # Clamp acceleration to limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

    def reset_controllers(self):
        """Reset PID controller states."""
        self.pid_speed.reset()
        self.pid_distance.reset()

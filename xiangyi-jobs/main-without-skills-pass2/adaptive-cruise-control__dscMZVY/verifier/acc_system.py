import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with multi-mode operation."""
    
    def __init__(self, config):
        """Initialize ACC system.
        
        Args:
            config: Configuration dictionary from vehicle_params.yaml
        """
        self.config = config
        
        # Vehicle parameters
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # ACC settings
        acc_cfg = config['acc_settings']
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.min_distance = acc_cfg['min_distance']
        self.emergency_ttc = acc_cfg['emergency_ttc_threshold']
        
        # PID controllers
        speed_pid = config['pid_speed']
        distance_pid = config['pid_distance']
        
        self.speed_controller = PIDController(
            speed_pid['kp'], speed_pid['ki'], speed_pid['kd']
        )
        self.distance_controller = PIDController(
            distance_pid['kp'], distance_pid['ki'], distance_pid['kd']
        )
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute ACC control command.
        
        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Acceleration command (m/s^2)
                - mode: Control mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error in follow mode (m) or None
        """
        distance_error = None
        
        # Determine control mode
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
        else:
            # Lead vehicle detected
            # Calculate safe following distance
            safe_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = safe_distance - distance
            
            # Calculate Time-To-Collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
            
            # Check emergency condition
            if ttc < self.emergency_ttc and relative_speed > 0:
                mode = 'emergency'
                # Apply maximum deceleration
                accel_cmd = self.max_decel
            else:
                mode = 'follow'
                # Use distance error to control speed
                accel_cmd = self.distance_controller.compute(distance_error, dt)
        
        # Clamp acceleration to limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return accel_cmd, mode, distance_error

import yaml
from pid_controller import PIDController

class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control."""
    
    def __init__(self, config):
        """Initialize ACC system with configuration.
        
        Args:
            config: Nested dictionary from vehicle_params.yaml
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']
        
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # PID controllers (will be initialized with tuned gains later)
        self.speed_pid = None
        self.distance_pid = None
    
    def set_pid_controllers(self, speed_gains, distance_gains):
        """Set PID controllers with tuned gains.
        
        Args:
            speed_gains: Dict with keys 'kp', 'ki', 'kd' for speed control
            distance_gains: Dict with keys 'kp', 'ki', 'kd' for distance control
        """
        self.speed_pid = PIDController(
            speed_gains['kp'],
            speed_gains['ki'],
            speed_gains['kd']
        )
        self.distance_pid = PIDController(
            distance_gains['kp'],
            distance_gains['ki'],
            distance_gains['kd']
        )
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command and determine control mode.
        
        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Control mode ('cruise', 'follow', 'emergency')
                - distance_error: Distance error (m) or None in cruise mode
        """
        # Determine mode
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise mode
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None
        else:
            # Lead vehicle detected - check TTC for emergency
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
            
            if ttc < self.emergency_ttc_threshold:
                # Emergency braking mode
                mode = 'emergency'
                acceleration_cmd = self.max_deceleration
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance
            else:
                # Follow mode
                mode = 'follow'
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance
                
                # Use distance PID to compute target speed adjustment
                distance_correction = self.distance_pid.compute(distance_error, dt)
                target_speed = lead_speed + distance_correction
                
                # Limit target speed to set speed
                target_speed = min(target_speed, self.set_speed)
                
                # Use speed PID to compute acceleration
                speed_error = target_speed - ego_speed
                acceleration_cmd = self.speed_pid.compute(speed_error, dt)
        
        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

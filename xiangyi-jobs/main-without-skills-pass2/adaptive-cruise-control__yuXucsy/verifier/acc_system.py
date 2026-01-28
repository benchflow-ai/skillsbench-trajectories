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
        
        # PID controllers - will be initialized with tuned parameters
        self.speed_pid = None
        self.distance_pid = None
    
    def set_pid_controllers(self, speed_params, distance_params):
        """Set PID controllers with tuned parameters.
        
        Args:
            speed_params: Dict with kp, ki, kd for speed control
            distance_params: Dict with kp, ki, kd for distance control
        """
        self.speed_pid = PIDController(
            speed_params['kp'],
            speed_params['ki'],
            speed_params['kd']
        )
        self.distance_pid = PIDController(
            distance_params['kp'],
            distance_params['ki'],
            distance_params['kd']
        )
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.
        
        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error in following distance (m) or None
        """
        # Mode 1: Cruise mode (no lead vehicle)
        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel = self.speed_pid.compute(speed_error, dt)
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
                mode = 'emergency'
                # Apply maximum deceleration
                accel = self.max_deceleration
                # Calculate desired distance for error reporting
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
            # Mode 3: Follow mode
            else:
                mode = 'follow'
                # Desired following distance: min_distance + time_headway * ego_speed
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
                
                # Use distance PID to compute target acceleration
                accel = self.distance_pid.compute(distance_error, dt)
        
        # Clamp acceleration to vehicle limits
        accel = max(self.max_deceleration, min(self.max_acceleration, accel))
        
        return (accel, mode, distance_error)

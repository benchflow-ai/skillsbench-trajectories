import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    """Adaptive Cruise Control system."""
    
    def __init__(self, config):
        """Initialize ACC system.
        
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
        
        # PID controllers
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )
        
        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command based on current state.
        
        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Control mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error (m) or None in cruise mode
        """
        # No lead vehicle - cruise control mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
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
                # Apply maximum deceleration
                acceleration_cmd = self.max_deceleration
                # Calculate desired distance for error reporting
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
            else:
                # Follow mode - maintain safe following distance
                mode = 'follow'
                # Desired distance based on time headway
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
                
                # Use distance PID controller
                acceleration_cmd = self.distance_pid.compute(distance_error, dt)
        
        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

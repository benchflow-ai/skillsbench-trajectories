import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with PID-based speed and distance control."""
    
    def __init__(self, config):
        """
        Initialize ACC system.
        
        Args:
            config: Configuration dictionary from vehicle_params.yaml
        """
        self.config = config
        
        # Vehicle parameters
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # PID controllers
        speed_pid = config['pid_speed']
        distance_pid = config['pid_distance']
        
        self.speed_controller = PIDController(
            speed_pid['kp'], speed_pid['ki'], speed_pid['kd']
        )
        self.distance_controller = PIDController(
            distance_pid['kp'], distance_pid['ki'], distance_pid['kd']
        )
        
        self.dt = config['simulation']['dt']
    
    def compute(self, ego_speed, lead_speed, distance, dt=None):
        """
        Compute acceleration command based on current state.
        
        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (uses config dt if not provided)
        
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', 'emergency')
                - distance_error: Error in distance (m) or None if no lead vehicle
        """
        if dt is None:
            dt = self.dt
        
        distance_error = None
        
        # Determine mode and compute acceleration
        if lead_speed is None or distance is None:
            # Cruise mode: no lead vehicle detected
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
        else:
            # Lead vehicle detected - calculate TTC
            speed_diff = ego_speed - lead_speed
            if speed_diff > 0.001:  # Avoid division by very small numbers
                ttc = distance / speed_diff
            else:
                ttc = float('inf')
            
            # Check for emergency condition
            if ttc < self.emergency_ttc_threshold and speed_diff > 0:
                mode = 'emergency'
                # Emergency braking
                accel_cmd = self.max_decel
            else:
                mode = 'follow'
                
                # In follow mode, use lead vehicle speed as target if it's below set speed
                target_speed = min(lead_speed, self.set_speed)
                speed_error = target_speed - ego_speed
                speed_accel = self.speed_controller.compute(speed_error, dt)
                
                # Also compute distance control
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = desired_distance - distance
                distance_accel = self.distance_controller.compute(distance_error, dt)
                
                # Blend the two controllers: prioritize distance safety
                # If distance is too small, decelerate; if too large, accelerate
                if distance < self.min_distance + 5:  # Safety margin
                    # Distance is critical, use distance control
                    accel_cmd = distance_accel
                else:
                    # Distance is OK, use speed control
                    accel_cmd = speed_accel
        
        # Constrain acceleration to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return (accel_cmd, mode, distance_error)

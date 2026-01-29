
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.acc_settings = config['acc_settings']
        self.vehicle_params = config['vehicle']
        
        # Initialize controllers with gains from config
        self.pid_speed = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )
        
        self.set_speed = float(self.acc_settings['set_speed'])
        self.time_headway = float(self.acc_settings['time_headway'])
        self.min_distance = float(self.acc_settings['min_distance'])
        self.emergency_ttc_threshold = float(self.acc_settings['emergency_ttc_threshold'])
        self.max_accel = float(self.vehicle_params['max_acceleration'])
        self.max_decel = float(self.vehicle_params['max_deceleration'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Computes acceleration command, mode, and distance error.
        
        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)
            
        Returns:
            (acceleration_cmd, mode, distance_error)
        """
        acceleration_cmd = 0.0
        mode = 'cruise'
        distance_error = None
        
        # Detect mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
        else:
            # Check for emergency
            ttc = float('inf')
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Compute control based on mode
        if mode == 'cruise':
            # Speed control
            error = self.set_speed - ego_speed
            raw_accel = self.pid_speed.compute(error, dt)
            acceleration_cmd = raw_accel
            
            # Reset distance PID to prevent windup
            self.pid_distance.reset()
            
        elif mode == 'emergency':
            # Emergency braking
            acceleration_cmd = self.max_decel
            
            # Reset PIDs
            self.pid_speed.reset()
            self.pid_distance.reset()
            
            # Calculate distance error for reporting even in emergency
            safe_distance = self.min_distance + (self.time_headway * ego_speed)
            distance_error = distance - safe_distance

        elif mode == 'follow':
            # Distance control
            safe_distance = self.min_distance + (self.time_headway * ego_speed)
            error = distance - safe_distance # Positive error means we are too far, need to speed up (accel > 0)
            
            # Use distance PID output directly to ensure tracking
            raw_accel_dist = self.pid_distance.compute(error, dt)
            
            acceleration_cmd = raw_accel_dist
            distance_error = error
            
            # Reset speed PID to prevent windup while inactive
            self.pid_speed.reset()



        # Clamp acceleration
        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

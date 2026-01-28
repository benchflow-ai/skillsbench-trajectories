from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PIDs
        # Speed PID
        ps = config['pid_speed']
        self.pid_speed = PIDController(ps['kp'], ps['ki'], ps['kd'])
        
        # Distance PID
        pd = config['pid_distance']
        self.pid_distance = PIDController(pd['kp'], pd['ki'], pd['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Returns (acceleration_cmd, mode, distance_error)
        """
        # Determine if lead vehicle is present
        if lead_speed is None or distance is None:
            mode = 'cruise'
            # Speed Control
            error = self.set_speed - ego_speed
            acc_cmd = self.pid_speed.compute(error, dt)
            dist_error = None
            
            # Reset distance PID
            self.pid_distance.reset()
            
        else:
            # Calculate TTC
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.001: 
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
            
            # Determine Mode
            if ttc < self.ttc_threshold:
                mode = 'emergency'
                acc_cmd = self.max_decel # Full braking
                
                target_distance = max(self.min_distance, ego_speed * self.time_headway)
                dist_error = distance - target_distance
                
                # Reset PIDs
                self.pid_speed.reset()
                self.pid_distance.reset()
                
            else:
                mode = 'follow'
                
                # Distance Control
                target_distance = max(self.min_distance, ego_speed * self.time_headway)
                dist_error = distance - target_distance
                
                dist_cmd = self.pid_distance.compute(dist_error, dt)
                
                # Speed Control (as limit)
                speed_error = self.set_speed - ego_speed
                speed_cmd = self.pid_speed.compute(speed_error, dt)
                
                # Take the more conservative command (min acceleration)
                # This ensures we don't exceed set speed while following
                # And we don't crash if speed limit is high
                acc_cmd = min(dist_cmd, speed_cmd)

        # Clamp acceleration
        acc_cmd = max(self.max_decel, min(self.max_accel, acc_cmd))
        
        return acc_cmd, mode, dist_error

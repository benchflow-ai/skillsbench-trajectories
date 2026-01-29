import math

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        from pid_controller import PIDController
        
        speed_conf = config.get('pid_speed', {'kp': 0.5, 'ki': 0.0, 'kd': 0.0})
        dist_conf = config.get('pid_distance', {'kp': 0.5, 'ki': 0.0, 'kd': 0.0})
        
        self.speed_pid = PIDController(speed_conf['kp'], speed_conf['ki'], speed_conf['kd'])
        self.dist_pid = PIDController(dist_conf['kp'], dist_conf['ki'], dist_conf['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Returns (acceleration_cmd, mode, distance_error)
        """
        mode = 'cruise'
        ttc = float('inf')
        
        if lead_speed is not None and distance is not None and not math.isnan(lead_speed) and not math.isnan(distance):
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
        
        # Speed Control (Cruise)
        # Target: set_speed
        acc_cruise = self.speed_pid.compute(self.set_speed - ego_speed, dt)
        
        acceleration_cmd = 0.0
        distance_error = None
        
        if mode == 'cruise':
            acceleration_cmd = acc_cruise
            
        elif mode == 'emergency':
            acceleration_cmd = self.max_decel
            # Calculate distance error just for logging
            if distance is not None:
                safe_dist = ego_speed * self.time_headway + self.min_distance
                distance_error = distance - safe_dist
                
        elif mode == 'follow':
            # Distance Control
            safe_dist = ego_speed * self.time_headway + self.min_distance
            dist_error = distance - safe_dist
            distance_error = dist_error
            
            acc_follow = self.dist_pid.compute(dist_error, dt)
            
            # Min-Select Strategy:
            # We want to maintain safe distance (acc_follow) BUT not exceed set_speed (acc_cruise)
            # If acc_follow > acc_cruise (gap is large, want to speed up), we clamp to acc_cruise.
            # If acc_follow < acc_cruise (gap is small, need to slow down), we use acc_follow.
            acceleration_cmd = min(acc_cruise, acc_follow)
            
        # Physical Limits
        acceleration_cmd = max(self.max_decel, min(acceleration_cmd, self.max_accel))
        
        return acceleration_cmd, mode, distance_error
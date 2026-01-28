from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PIDs with limits
        # Speed control limits: [max_decel, max_accel]
        self.speed_pid = PIDController(0.1, 0.0, 0.0, self.max_decel, self.max_accel)
        
        # Distance control limits: [max_decel, max_accel]
        self.dist_pid = PIDController(0.1, 0.0, 0.0, self.max_decel, self.max_accel)

    def update_gains(self, speed_gains, dist_gains):
        self.speed_pid.kp = speed_gains['kp']
        self.speed_pid.ki = speed_gains['ki']
        self.speed_pid.kd = speed_gains['kd']
        self.dist_pid.kp = dist_gains['kp']
        self.dist_pid.ki = dist_gains['ki']
        self.dist_pid.kd = dist_gains['kd']
        self.speed_pid.reset()
        self.dist_pid.reset()

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        ttc = None
        
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
            
            if ttc is not None and ttc < self.emergency_ttc:
                mode = 'emergency'
            else:
                mode = 'follow'
        
        acceleration_cmd = 0.0
        distance_error = None
        
        if mode == 'emergency':
            acceleration_cmd = self.max_decel
            safe_dist = self.min_distance + ego_speed * self.time_headway
            distance_error = safe_dist - distance
            
        elif mode == 'follow':
            safe_dist = self.min_distance + ego_speed * self.time_headway
            # Error definition: we want distance >= safe_dist.
            # If distance < safe_dist, error is negative? 
            # Standard PID: we want PV (distance) to equal SP (safe_dist).
            # error = SP - PV = safe_dist - distance.
            # If safe_dist > distance (too close), error > 0.
            # We want to slow down (negative accel). 
            # So we need negative gain? Or define error as distance - safe_dist?
            # If distance > safe_dist (too far), error > 0. We want positive accel.
            # So error = distance - safe_dist.
            
            error = distance - safe_dist
            distance_error = safe_dist - distance # Report positive if too close?
            # Task says "distance steady-state error". Usually |target - actual|.
            
            # Compute distance control output
            dist_accel = self.dist_pid.compute(error, dt)
            
            # Compute speed control output (limit)
            speed_error = self.set_speed - ego_speed
            speed_accel = self.speed_pid.compute(speed_error, dt)
            
            # Take minimum (safest) acceleration
            acceleration_cmd = min(dist_accel, speed_accel)
            
        else: # cruise
            error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(error, dt)
            distance_error = None
            
        acceleration_cmd = max(self.max_decel, min(acceleration_cmd, self.max_accel))
        
        return acceleration_cmd, mode, distance_error

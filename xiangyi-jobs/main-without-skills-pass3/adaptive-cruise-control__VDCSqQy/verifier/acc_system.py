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
        
        # Initialize PIDs with config values
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
        mode = 'cruise'
        accel_cmd = 0.0
        dist_error = None
        
        # Check if lead vehicle is present
        if lead_speed is None or distance is None or str(lead_speed) == 'nan' or str(distance) == 'nan':
            mode = 'cruise'
            # Cruise Control
            error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(error, dt)
            # Reset distance PID to prevent windup
            self.distance_pid.reset()
        else:
            # Lead vehicle detected
            # Calculate TTC
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.001:
                ttc = distance / rel_speed
            else:
                ttc = float('inf')
            
            if ttc < self.ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
                # Optional: Reset PIDs
            else:
                mode = 'follow'
                
                # Distance Control
                # Desired distance
                safe_dist = self.min_distance + ego_speed * self.time_headway
                dist_error = distance - safe_dist
                
                # PID on distance error
                # If distance > safe_dist (positive error), we want positive accel? 
                # Yes, to close gap? No, usually we want to maintain gap.
                # If distance > safe_dist, we are far, we can accelerate.
                # If distance < safe_dist, we are close, we need to brake (negative accel).
                accel_dist = self.distance_pid.compute(dist_error, dt)
                
                # Speed Control (limit)
                speed_error = self.set_speed - ego_speed
                accel_speed = self.speed_pid.compute(speed_error, dt)
                
                # Take minimum for safety (don't exceed set speed, don't crash)
                accel_cmd = min(accel_speed, accel_dist)
        
        # Clamp acceleration
        accel_cmd = max(min(accel_cmd, self.max_accel), self.max_decel)
        
        return accel_cmd, mode, dist_error

from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        # Handle typo fallback
        if 'max_deceleration' in config['vehicle']:
             self.max_decel = config['vehicle']['max_deceleration']
        elif 'max_decelaration' in config['vehicle']:
             self.max_decel = config['vehicle']['max_decelaration']
        else:
             self.max_decel = -8.0
        
        speed_conf = config['pid_speed']
        dist_conf = config['pid_distance']
        
        limits = (self.max_decel, self.max_accel)
        
        self.pid_speed = PIDController(
            speed_conf['kp'], speed_conf['ki'], speed_conf['kd'], 
            output_limits=limits
        )
        self.pid_distance = PIDController(
            dist_conf['kp'], dist_conf['ki'], dist_conf['kd'], 
            output_limits=limits
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Returns: (acceleration_cmd, mode, distance_error)
        """
        # 1. Compute Speed Control Command (Always active as limit)
        speed_error = self.set_speed - ego_speed
        speed_cmd = self.pid_speed.compute(speed_error, dt)
        
        mode = 'cruise'
        dist_cmd = float('inf')
        distance_error = None
        
        # 2. Determine Situation
        if lead_speed is not None and distance is not None:
            # Check Emergency
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
                
            if ttc < self.emergency_ttc:
                mode = 'emergency'
            else:
                mode = 'follow'
                
        # 3. Compute Distance Command if needed
        if mode == 'follow':
            safe_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - safe_distance
            # Error < 0 means too close -> Decel.
            dist_cmd = self.pid_distance.compute(distance_error, dt)
            
        elif mode == 'emergency':
            dist_cmd = self.max_decel
            distance_error = distance - (self.min_distance + self.time_headway * ego_speed)
            # In emergency, we ignore comfort/speed, just brake.
            
        # 4. Arbitration
        if mode == 'cruise':
            final_cmd = speed_cmd
            # Reset dist PID
            self.pid_distance.reset()
            
        elif mode == 'emergency':
            final_cmd = self.max_decel
            # Reset both? Or just override.
            self.pid_speed.reset()
            self.pid_distance.reset()
            
        else: # follow
            # Standard ACC: Min of SpeedCmd and DistCmd
            # This ensures we don't exceed set_speed AND we don't hit lead.
            
            if speed_cmd < dist_cmd:
                final_cmd = speed_cmd
                # We are speed limited (Lead is fast/far).
                # Effectively Cruise behavior in Follow mode.
                # Reset Dist PID to avoid windup?
                # Maybe not? If we get closer, Dist PID should be ready.
                # But if we integrate error while ignored, we wind up.
                # Yes, reset the one NOT used.
                self.pid_distance.reset()
            else:
                final_cmd = dist_cmd
                # We are distance limited (Lead is slow).
                # Reset Speed PID?
                self.pid_speed.reset()

        # Clamp
        final_cmd = max(self.max_decel, min(self.max_accel, final_cmd))
        
        return final_cmd, mode, distance_error

from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PIDs with values from config (which might be updated by simulation.py)
        # Assuming config structure matches vehicle_params.yaml + tuning_results updates
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

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        accel_cmd = 0.0
        dist_error = None
        
        # Calculate Cruise Acceleration (always active as upper bound)
        error_speed = self.set_speed - ego_speed
        accel_cruise = self.pid_speed.compute(error_speed, dt)
        
        # Determine Mode and Final Acceleration
        if lead_speed is None or distance is None:
            # No vehicle -> Cruise
            mode = 'cruise'
            accel_cmd = accel_cruise
            # Reset distance PID just in case
            self.pid_distance.reset()
        else:
            # Vehicle detected
            # Calculate TTC
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
            
            if ttc < self.emergency_ttc:
                mode = 'emergency'
                accel_cmd = self.max_decel
                # Log distance error for reference
                desired_distance = self.min_distance + (self.time_headway * ego_speed)
                dist_error = distance - desired_distance
                self.pid_speed.reset()
                self.pid_distance.reset()
            else:
                # Follow Mode Calculation
                desired_distance = self.min_distance + (self.time_headway * ego_speed)
                dist_error = distance - desired_distance
                
                # PID on distance error
                accel_follow = self.pid_distance.compute(dist_error, dt)
                
                # ISO-style ACC: take min of cruise and follow
                if accel_follow < accel_cruise:
                    accel_cmd = accel_follow
                    mode = 'follow'
                    # Reset speed integrator? Since Ki=0, it doesn't matter.
                    # But good practice:
                    # self.pid_speed.reset() 
                else:
                    accel_cmd = accel_cruise
                    mode = 'cruise' # We are ignoring the lead car because it's faster/farther than our set speed allows
                    # self.pid_distance.reset()

        # Clamp acceleration
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return accel_cmd, mode, dist_error

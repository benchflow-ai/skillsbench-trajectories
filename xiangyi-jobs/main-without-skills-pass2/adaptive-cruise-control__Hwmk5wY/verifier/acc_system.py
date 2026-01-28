from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.vehicle_specs = config['vehicle']
        self.acc_settings = config['acc_settings']
        
        # Initialize PIDs from config
        # Expecting config to have updated PID values from tuning_results.yaml
        pid_speed_cfg = config['pid_speed']
        self.pid_speed = PIDController(
            pid_speed_cfg['kp'],
            pid_speed_cfg['ki'],
            pid_speed_cfg['kd']
        )
        
        pid_dist_cfg = config['pid_distance']
        self.pid_distance = PIDController(
            pid_dist_cfg['kp'],
            pid_dist_cfg['ki'],
            pid_dist_cfg['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Computes the acceleration command based on the current state.
        
        Args:
            ego_speed: Current speed of the ego vehicle (m/s)
            lead_speed: Speed of the lead vehicle (m/s) or None
            distance: Distance to the lead vehicle (m) or None
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        
        # Calculate Cruise Command (Always active candidate)
        target_speed = self.acc_settings['set_speed']
        speed_error = target_speed - ego_speed
        accel_cruise = self.pid_speed.compute(speed_error, dt)
        
        # Determine Mode and Final Command
        mode = 'cruise'
        acceleration_cmd = accel_cruise
        distance_error = None
        
        if lead_speed is not None and distance is not None and not (isinstance(lead_speed, float) and lead_speed != lead_speed):
            # Vehicle detected
            
            # Check Emergency
            ttc = float('inf')
            if ego_speed > lead_speed:
                ttc = distance / (ego_speed - lead_speed)
                
            if ttc < self.acc_settings['emergency_ttc_threshold']:
                mode = 'emergency'
                acceleration_cmd = self.vehicle_specs['max_deceleration']
                self.pid_speed.reset()
                self.pid_distance.reset()
                
                # Calculate dist error for logging
                safe_distance = self.acc_settings['min_distance'] + (self.acc_settings['time_headway'] * ego_speed)
                distance_error = distance - safe_distance
                
            else:
                # Follow Logic
                safe_distance = self.acc_settings['min_distance'] + (self.acc_settings['time_headway'] * ego_speed)
                distance_error = distance - safe_distance
                accel_follow = self.pid_distance.compute(distance_error, dt)
                
                if accel_follow < accel_cruise:
                    mode = 'follow'
                    acceleration_cmd = accel_follow
                    # Reset speed PID to keep it clean (though Ki=0 usually)
                    # self.pid_speed.reset() 
                    # Actually, if we reset speed PID, we lose D-term history for smooth handover?
                    # But we are in follow mode, so speed control is inactive.
                    self.pid_speed.reset()
                else:
                    mode = 'cruise'
                    acceleration_cmd = accel_cruise
                    self.pid_distance.reset()
        else:
            # No vehicle
            mode = 'cruise'
            acceleration_cmd = accel_cruise
            self.pid_distance.reset()

        # Clamp Acceleration
        max_accel = self.vehicle_specs['max_acceleration']
        max_decel = self.vehicle_specs['max_deceleration']
        
        acceleration_cmd = max(max_decel, min(acceleration_cmd, max_accel))
        
        return acceleration_cmd, mode, distance_error

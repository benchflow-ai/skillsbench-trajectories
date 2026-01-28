from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
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
        # Always compute cruise acceleration
        speed_error = self.set_speed - ego_speed
        accel_cruise = self.pid_speed.compute(speed_error, dt)
        
        mode = 'cruise'
        acceleration_cmd = accel_cruise
        distance_error = None
        
        lead_exists = lead_speed is not None and distance is not None
        
        if lead_exists:
            ttc = float('inf')
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_decel
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance
            else:
                mode = 'follow'
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = distance - desired_distance
                accel_follow = self.pid_distance.compute(distance_error, dt)
                # ACC logic: follow the lead but don't exceed set speed
                acceleration_cmd = min(accel_cruise, accel_follow)
        
        # Apply constraints
        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error
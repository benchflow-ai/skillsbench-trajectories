from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_config = config['acc_settings']
        self.set_speed = acc_config['set_speed']
        self.time_headway = acc_config['time_headway']
        self.min_distance = acc_config['min_distance']
        self.emergency_ttc_threshold = acc_config['emergency_ttc_threshold']
        
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
        self.current_mode = 'cruise'

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        distance_error = None
        ttc = None
        
        if distance is not None and not (isinstance(distance, float) and distance != distance):
            if lead_speed is not None and not (isinstance(lead_speed, float) and lead_speed != lead_speed):
                relative_speed = ego_speed - lead_speed
                if relative_speed > 0:
                    ttc = distance / relative_speed
                
                if ttc is not None and ttc < self.emergency_ttc_threshold:
                    mode = 'emergency'
                else:
                    mode = 'follow'
            else:
                mode = 'follow'
        
        if mode != self.current_mode:
            self.pid_speed.reset()
            self.pid_distance.reset()
            self.current_mode = mode

        if mode == 'emergency':
            accel_cmd = self.max_decel
        elif mode == 'follow':
            target_distance = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - target_distance
            # In follow mode, we want distance_error to be 0.
            # PID for distance: error = current_distance - target_distance
            # If distance > target_distance, error > 0, we want positive accel?
            # Actually, standard distance PID: error = distance - target_distance.
            accel_cmd = self.pid_distance.compute(distance_error, dt)
            
            # Also limit by speed PID if we are going too fast? 
            # Usually ACC follow mode also considers set_speed as a cap.
            speed_error = self.set_speed - ego_speed
            accel_speed = self.pid_speed.compute(speed_error, dt)
            accel_cmd = min(accel_cmd, accel_speed)
        else: # cruise
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
        
        # Clamp acceleration
        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        
        return accel_cmd, mode, distance_error

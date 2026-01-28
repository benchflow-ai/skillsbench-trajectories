from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
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
        mode = 'cruise'
        acceleration_cmd = 0.0
        distance_error = None
        
        if distance is not None and lead_speed is not None:
            rel_speed = ego_speed - lead_speed
            ttc = float('inf')
            if rel_speed > 0:
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_decel
                safe_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - safe_distance
            else:
                mode = 'follow'
                safe_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - safe_distance
                acceleration_cmd = self.pid_distance.compute(distance_error, dt)
        else:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None

        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

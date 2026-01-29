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
        ttc = float('inf')

        if lead_speed is not None and distance is not None and distance > 0:
            if ego_speed > lead_speed:
                ttc = distance / (ego_speed - lead_speed)
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_decel
            else:
                mode = 'follow'
                d_target = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - d_target
                acceleration_cmd = self.pid_distance.compute(distance_error, dt)
        else:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            # Reset distance PID to prevent integral windup when not in follow mode
            self.pid_distance.reset()

        # Apply constraints
        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

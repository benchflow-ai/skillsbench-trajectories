from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_acc = config['vehicle']['max_acceleration']
        self.max_dec = config['vehicle']['max_deceleration']
        
        self.pid_speed = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd'],
            output_limits=(self.max_dec, self.max_acc)
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd'],
            output_limits=(self.max_dec, self.max_acc)
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        distance_error = None
        acceleration_cmd = 0.0
        ttc = float('inf')
        
        speed_error = self.set_speed - ego_speed
        acc_cruise = self.pid_speed.compute(speed_error, dt)

        if lead_speed is not None and not (isinstance(lead_speed, str) and lead_speed == '') and distance is not None and not (isinstance(distance, str) and distance == ''):
            lead_speed = float(lead_speed)
            distance = float(distance)
            
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_dec
            else:
                mode = 'follow'
                target_distance = ego_speed * self.time_headway + self.min_distance
                distance_error = distance - target_distance
                acc_follow = self.pid_distance.compute(distance_error, dt)
                acceleration_cmd = min(acc_cruise, acc_follow)
        else:
            mode = 'cruise'
            acceleration_cmd = acc_cruise

        acceleration_cmd = max(self.max_dec, min(self.max_acc, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error, ttc

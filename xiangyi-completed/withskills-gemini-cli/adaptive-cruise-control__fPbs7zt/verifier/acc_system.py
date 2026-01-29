import math
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
        mode = 'cruise'
        ttc = None
        distance_error = None
        
        if lead_speed is None or math.isnan(lead_speed) or distance is None or math.isnan(distance):
            mode = 'cruise'
        else:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        if mode == 'cruise':
            error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
            self.pid_distance.reset()
        elif mode == 'emergency':
            accel_cmd = self.max_decel
            self.pid_speed.reset()
            self.pid_distance.reset()
        else: # follow
            d_safe = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - d_safe
            accel_cmd = self.pid_distance.compute(distance_error, dt)
            self.pid_speed.reset()
            
        # Clamp acceleration
        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        
        return accel_cmd, mode, distance_error

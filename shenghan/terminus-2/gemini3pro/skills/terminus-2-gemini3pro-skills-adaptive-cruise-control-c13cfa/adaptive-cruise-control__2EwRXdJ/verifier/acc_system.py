import yaml
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
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
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            ttc = distance / relative_speed if relative_speed > 0 else float('inf')
            
            if ttc < self.ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
        
        acceleration_cmd = 0.0
        distance_error = None
        
        if mode == 'cruise':
            error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(error, dt)
            self.distance_pid.reset()
            
        elif mode == 'follow':
            safe_distance = self.time_headway * ego_speed + self.min_distance
            # Error is defined such that positive error means we are too far (speed up)
            # Negative error means we are too close (slow down)
            error = distance - safe_distance
            acceleration_cmd = self.distance_pid.compute(error, dt)
            distance_error = error
            self.speed_pid.reset()
            
        elif mode == 'emergency':
            acceleration_cmd = self.max_decel
            distance_error = distance - (self.time_headway * ego_speed + self.min_distance)
            self.speed_pid.reset()
            self.distance_pid.reset()
            
        acceleration_cmd = max(self.max_decel, min(acceleration_cmd, self.max_accel))
        
        return acceleration_cmd, mode, distance_error

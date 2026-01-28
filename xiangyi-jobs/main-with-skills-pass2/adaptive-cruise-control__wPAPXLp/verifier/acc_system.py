
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_cfg = config['acc_settings']
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.min_distance = acc_cfg['min_distance']
        self.emergency_ttc_threshold = acc_cfg['emergency_ttc_threshold']
        
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
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        distance_error = None
        
        if lead_speed is None or distance is None:
            # Cruise mode
            error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
            mode = 'cruise'
        else:
            # Check for emergency
            relative_speed = ego_speed - lead_speed
            ttc = float('inf')
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
            else:
                mode = 'follow'
                target_distance = ego_speed * self.time_headway + self.min_distance
                distance_error = distance - target_distance
                accel_cmd = self.pid_distance.compute(distance_error, dt)
        
        # Apply constraints
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return accel_cmd, mode, distance_error

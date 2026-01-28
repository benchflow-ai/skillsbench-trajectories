import yaml
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_cfg = config['acc_settings']
        veh_cfg = config['vehicle']
        
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.min_distance = acc_cfg['min_distance']
        self.emergency_ttc_threshold = acc_cfg['emergency_ttc_threshold']
        
        self.max_accel = veh_cfg['max_acceleration']
        self.max_decel = veh_cfg['max_deceleration']
        
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
        self.prev_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        try:
            if distance is None or distance == '' or str(distance).lower() == 'nan':
                dist = None
            else:
                dist = float(distance)
        except (TypeError, ValueError):
            dist = None
            
        try:
            if lead_speed is None or lead_speed == '' or str(lead_speed).lower() == 'nan':
                l_speed = None
            else:
                l_speed = float(lead_speed)
        except (TypeError, ValueError):
            l_speed = None

        if dist is None or l_speed is None:
            mode = 'cruise'
            distance_error = None
            error = self.set_speed - ego_speed
            if self.prev_mode != 'cruise':
                self.pid_speed.reset()
            accel = self.pid_speed.compute(error, dt)
        else:
            rel_speed = ego_speed - l_speed
            ttc = dist / rel_speed if rel_speed > 0 else float('inf')
            
            target_distance = self.min_distance + ego_speed * self.time_headway
            distance_error = dist - target_distance

            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel = self.max_decel
            else:
                mode = 'follow'
                if self.prev_mode != 'follow':
                    self.pid_distance.reset()
                accel = self.pid_distance.compute(distance_error, dt)
        
        accel = max(self.max_decel, min(self.max_accel, accel))
        self.prev_mode = mode
        return accel, mode, distance_error

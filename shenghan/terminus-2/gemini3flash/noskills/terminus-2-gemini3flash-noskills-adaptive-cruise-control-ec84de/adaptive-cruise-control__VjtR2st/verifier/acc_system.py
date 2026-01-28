from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.acc_cfg = config['acc_settings']
        self.veh_cfg = config['vehicle']
        
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
        self.last_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        if lead_speed is None or distance is None or distance == '' or lead_speed == '':
            mode = 'cruise'
            if self.last_mode != 'cruise':
                self.pid_speed.reset()
            error = self.acc_cfg['set_speed'] - ego_speed
            accel = self.pid_speed.compute(error, dt)
            dist_error = None
        else:
            lead_speed = float(lead_speed)
            distance = float(distance)
            
            ttc = float('inf')
            if ego_speed > lead_speed:
                ttc = distance / (ego_speed - lead_speed)
            
            if ttc < self.acc_cfg['emergency_ttc_threshold']:
                mode = 'emergency'
                accel = self.veh_cfg['max_deceleration']
                d_safe = self.acc_cfg['min_distance'] + self.acc_cfg['time_headway'] * ego_speed
                dist_error = distance - d_safe
                self.pid_distance.reset()
            else:
                mode = 'follow'
                if self.last_mode not in ['follow', 'emergency']:
                    self.pid_distance.reset()
                d_safe = self.acc_cfg['min_distance'] + self.acc_cfg['time_headway'] * ego_speed
                dist_error = distance - d_safe
                accel = self.pid_distance.compute(dist_error, dt)
        
        accel = max(self.veh_cfg['max_deceleration'], min(self.veh_cfg['max_acceleration'], accel))
        self.last_mode = mode
        
        return accel, mode, dist_error

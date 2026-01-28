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
            config['pid_speed']['kd'],
            output_limits=(self.max_decel, self.max_accel)
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd'],
            output_limits=(self.max_decel, self.max_accel)
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = (lead_speed is not None and not math.isnan(lead_speed)) and (distance is not None and not math.isnan(distance))
        
        mode = 'cruise'
        ttc = float('inf')
        distance_error = None
        
        if lead_present:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
        
        if mode == 'cruise':
            error = self.set_speed - ego_speed
            accel = self.pid_speed.compute(error, dt)
        elif mode == 'follow':
            target_dist = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - target_dist
            accel = self.pid_distance.compute(distance_error, dt)
        else:
            accel = self.max_decel
            if distance is not None:
                target_dist = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - target_dist
            # Reset PIDs when in emergency
            self.pid_speed.reset()
            self.pid_distance.reset()

        accel = max(self.max_decel, min(self.max_accel, accel))
        return accel, mode, distance_error

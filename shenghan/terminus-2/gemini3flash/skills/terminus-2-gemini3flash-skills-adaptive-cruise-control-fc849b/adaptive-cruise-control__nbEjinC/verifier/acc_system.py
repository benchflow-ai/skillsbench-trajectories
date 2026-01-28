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
        self.last_accel = 0.0

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and not math.isnan(lead_speed) and distance is not None and not math.isnan(distance)
        
        ttc = None
        if lead_present:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed

        is_saturated = self.last_accel >= self.max_accel or self.last_accel <= self.max_decel
        
        # Always compute speed control
        speed_error = self.set_speed - ego_speed
        accel_speed = self.pid_speed.compute(speed_error, dt, is_saturated)
        
        mode = 'cruise'
        dist_error = None
        accel_cmd = accel_speed

        if lead_present:
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
                self.pid_speed.reset()
                self.pid_distance.reset()
            else:
                mode = 'follow'
                target_distance = ego_speed * self.time_headway + self.min_distance
                dist_error = distance - target_distance
                accel_dist = self.pid_distance.compute(dist_error, dt, is_saturated)
                # ACC logic: use the more conservative acceleration
                accel_cmd = min(accel_speed, accel_dist)
        else:
            self.pid_distance.reset()

        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        self.last_accel = accel_cmd
        
        return accel_cmd, mode, dist_error

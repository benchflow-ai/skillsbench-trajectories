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
        
        # We'll initialize PIDs with dummy values or load them later if needed.
        # But simulation.py will load from tuning_results.yaml.
        # For now, let's allow them to be set or passed.
        self.pid_speed = None
        self.pid_distance = None

    def set_pids(self, pid_speed_config, pid_distance_config):
        self.pid_speed = PIDController(pid_speed_config['kp'], pid_speed_config['ki'], pid_speed_config['kd'])
        self.pid_distance = PIDController(pid_distance_config['kp'], pid_distance_config['ki'], pid_distance_config['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        d_safe = self.min_distance + ego_speed * self.time_headway
        
        # Always compute speed-based acceleration
        speed_error = self.set_speed - ego_speed
        accel_speed = self.pid_speed.compute(speed_error, dt)
        
        if lead_speed is None or distance is None or math.isnan(lead_speed) or math.isnan(distance):
            mode = 'cruise'
            accel_cmd = accel_speed
            distance_error = None
        else:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
            else:
                ttc = float('inf')
            
            distance_error = distance - d_safe
            accel_dist = self.pid_distance.compute(distance_error, dt)
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
            else:
                mode = 'follow'
                # Standard ACC: Take minimum of speed control and distance control
                accel_cmd = min(accel_speed, accel_dist)
        
        # Clamp acceleration
        accel_cmd = max(min(accel_cmd, self.max_accel), self.max_decel)
        
        return accel_cmd, mode, distance_error

from pid_controller import PIDController
import math

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PID controllers with values from config (though they will be overridden by tuning results)
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

    def set_pid_params(self, speed_params, distance_params):
        self.pid_speed.kp = speed_params['kp']
        self.pid_speed.ki = speed_params['ki']
        self.pid_speed.kd = speed_params['kd']
        self.pid_distance.kp = distance_params['kp']
        self.pid_distance.ki = distance_params['ki']
        self.pid_distance.kd = distance_params['kd']

    def compute(self, ego_speed, lead_speed, distance, dt):
        prev_mode = getattr(self, 'current_mode', None)
        mode = 'cruise'
        distance_error = None
        
        if lead_speed is None or math.isnan(lead_speed) or distance is None or math.isnan(distance):
            mode = 'cruise'
            error = self.set_speed - ego_speed
            if prev_mode != 'cruise':
                self.pid_speed.reset()
            accel_cmd = self.pid_speed.compute(error, dt)
        else:
            rel_speed = ego_speed - lead_speed
            ttc = distance / rel_speed if rel_speed > 0 else float('inf')
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
            else:
                mode = 'follow'
            
            if prev_mode != mode:
                self.pid_distance.reset()
            
            # Distance error for follow and emergency (for reporting)
            target_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - target_distance
            
            if mode == 'follow':
                accel_cmd = self.pid_distance.compute(distance_error, dt)

        self.current_mode = mode
        # Apply constraints
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return accel_cmd, mode, distance_error

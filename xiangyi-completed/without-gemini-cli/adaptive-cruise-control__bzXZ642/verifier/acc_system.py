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
        distance_error = None
        ttc = float('inf')

        if lead_speed is not None and not math.isnan(lead_speed) and distance is not None and not math.isnan(distance):
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
            else:
                ttc = float('inf')

            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
            
            desired_distance = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - desired_distance
        else:
            mode = 'cruise'

        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt, limit=5.0)
            self.pid_distance.reset()
        elif mode == 'emergency':
            # Emergency braking
            accel_cmd = self.max_decel
            self.pid_speed.reset()
            # Still compute distance error for reporting
            desired_distance = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - desired_distance
        else: # follow
            accel_cmd = self.pid_distance.compute(distance_error, dt, limit=5.0)
            self.pid_speed.reset()

        # Apply constraints
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

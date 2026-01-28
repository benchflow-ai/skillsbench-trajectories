"""
Adaptive Cruise Control System Implementation
"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config, pid_speed_gains=None, pid_distance_gains=None):
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        if pid_speed_gains:
            speed_kp, speed_ki, speed_kd = pid_speed_gains['kp'], pid_speed_gains['ki'], pid_speed_gains['kd']
        else:
            speed_kp, speed_ki, speed_kd = config['pid_speed']['kp'], config['pid_speed']['ki'], config['pid_speed']['kd']
        
        if pid_distance_gains:
            dist_kp, dist_ki, dist_kd = pid_distance_gains['kp'], pid_distance_gains['ki'], pid_distance_gains['kd']
        else:
            dist_kp, dist_ki, dist_kd = config['pid_distance']['kp'], config['pid_distance']['ki'], config['pid_distance']['kd']
        
        self.speed_pid = PIDController(kp=speed_kp, ki=speed_ki, kd=speed_kd,
                                        output_min=self.max_decel, output_max=self.max_accel)
        self.distance_pid = PIDController(kp=dist_kp, ki=dist_ki, kd=dist_kd,
                                          output_min=self.max_decel, output_max=self.max_accel)
        self.prev_mode = 'cruise'

    def calculate_safe_distance(self, speed):
        return speed * self.time_headway + self.min_distance

    def calculate_ttc(self, distance, ego_speed, lead_speed):
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def determine_mode(self, lead_speed, ttc):
        if lead_speed is None:
            return 'cruise'
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            return 'emergency'
        return 'follow'

    def compute(self, ego_speed, lead_speed, distance, dt):
        ttc = None
        if lead_speed is not None and distance is not None:
            ttc = self.calculate_ttc(distance, ego_speed, lead_speed)
        
        mode = self.determine_mode(lead_speed, ttc)
        
        if mode != self.prev_mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
            self.prev_mode = mode
        
        distance_error = None
        
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
        elif mode == 'emergency':
            accel_cmd = self.max_decel
            if distance is not None:
                distance_error = distance - self.calculate_safe_distance(ego_speed)
        else:  # follow
            safe_dist = self.calculate_safe_distance(ego_speed)
            distance_error = distance - safe_dist
            speed_adjustment = distance_error * 0.2
            target_speed = max(0, min(self.set_speed, lead_speed + speed_adjustment))
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            if distance < self.min_distance:
                accel_cmd = min(accel_cmd, self.max_decel * 0.5)
            elif distance_error < -5:
                accel_cmd = min(accel_cmd, -2.0)
        
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        return accel_cmd, mode, distance_error

    def reset(self):
        self.speed_pid.reset()
        self.distance_pid.reset()
        self.prev_mode = 'cruise'

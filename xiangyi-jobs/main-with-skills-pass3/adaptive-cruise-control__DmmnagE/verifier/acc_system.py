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

        # Initialize with limits for anti-windup
        self.pid_speed = PIDController(0, 0, 0, output_min=self.max_decel, output_max=self.max_accel)
        self.pid_distance = PIDController(0, 0, 0, output_min=self.max_decel, output_max=self.max_accel)

    def set_pid_params(self, speed_params, distance_params):
        self.pid_speed.kp = speed_params['kp']
        self.pid_speed.ki = speed_params['ki']
        self.pid_speed.kd = speed_params['kd']
        self.pid_distance.kp = distance_params['kp']
        self.pid_distance.ki = distance_params['ki']
        self.pid_distance.kd = distance_params['kd']

    def compute(self, ego_speed, lead_speed, distance, dt):
        # Always compute speed control command
        speed_error = self.set_speed - ego_speed
        accel_speed = self.pid_speed.compute(speed_error, dt)
        
        mode = 'cruise'
        distance_error = None
        ttc = float('inf')
        accel_cmd = accel_speed

        if distance is not None and not math.isnan(distance):
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
                self.pid_distance.integral = 0
                self.pid_speed.integral = 0
            else:
                mode = 'follow'
                target_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - target_distance
                accel_dist = self.pid_distance.compute(distance_error, dt)
                # ACC logic: take the minimum of speed control and distance control
                accel_cmd = min(accel_speed, accel_dist)
        else:
            mode = 'cruise'
            # accel_cmd is already accel_speed
            self.pid_distance.reset()

        # Final safety clamp
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return accel_cmd, mode, distance_error, ttc

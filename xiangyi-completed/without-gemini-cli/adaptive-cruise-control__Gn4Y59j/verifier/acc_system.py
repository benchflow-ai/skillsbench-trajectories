
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
        acceleration_cmd = 0.0
        distance_error = None
        ttc = float('inf')

        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_decel
            else:
                mode = 'follow'
        
        if mode == 'cruise':
            error_speed = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(error_speed, dt)
            self.pid_distance.reset()
        elif mode == 'follow':
            target_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - target_distance
            acceleration_cmd = self.pid_distance.compute(distance_error, dt)
            self.pid_speed.reset()
            # Also limit follow acceleration by cruise control to not exceed set speed
            if ego_speed >= self.set_speed and acceleration_cmd > 0:
                 error_speed = self.set_speed - ego_speed
                 accel_speed = self.pid_speed.compute(error_speed, dt)
                 acceleration_cmd = min(acceleration_cmd, accel_speed)

        # Apply constraints
        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

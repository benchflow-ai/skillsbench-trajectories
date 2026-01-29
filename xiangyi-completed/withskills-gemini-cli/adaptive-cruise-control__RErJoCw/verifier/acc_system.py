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

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        
        ttc = None
        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        if not lead_present:
            mode = 'cruise'
        elif ttc is not None and ttc < self.acc_cfg['emergency_ttc_threshold']:
            mode = 'emergency'
        else:
            mode = 'follow'

        acceleration_cmd = 0.0
        distance_error = None

        if mode == 'cruise':
            speed_error = self.acc_cfg['set_speed'] - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            self.pid_distance.reset()
            
        elif mode == 'emergency':
            acceleration_cmd = self.veh_cfg['max_deceleration']
            self.pid_speed.reset()
            self.pid_distance.reset()
            
        elif mode == 'follow':
            # Distance control
            safe_dist = ego_speed * self.acc_cfg['time_headway'] + self.acc_cfg['min_distance']
            distance_error = distance - safe_dist
            accel_dist = self.pid_distance.compute(distance_error, dt)
            
            # Speed control (as a limit)
            speed_error = self.acc_cfg['set_speed'] - ego_speed
            accel_speed = self.pid_speed.compute(speed_error, dt)
            
            # Take minimum of both to stay safe and within speed limit
            # However, if distance_error is negative (too close), accel_dist will be negative.
            # We must prioritize safety (distance control) when too close.
            acceleration_cmd = min(accel_dist, accel_speed)
            
            # Note: We don't reset PIDs here as we use both
        
        # Apply physical limits
        acceleration_cmd = max(self.veh_cfg['max_deceleration'], 
                               min(acceleration_cmd, self.veh_cfg['max_acceleration']))

        return acceleration_cmd, mode, distance_error
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_cfg = config['acc_settings']
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.min_distance = acc_cfg['min_distance']
        self.emergency_ttc_threshold = acc_cfg['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # We need to initialize PID controllers, but the prompt says simulation.py reads gains from tuning_results.yaml.
        # However, AdaptiveCruiseControl needs these controllers.
        # I'll add a method to set/update PID gains if needed, or just initialize them with default and let simulation.py handle it.
        # Actually, let's pass the gains in the constructor or via a dedicated method.
        # The prompt says: Constructor: __init__(self, config) where config is nested dict from vehicle_params.yaml
        # vehicle_params.yaml HAS pid_speed and pid_distance sections.
        
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
        acceleration_cmd = 0.0
        
        has_lead = lead_speed is not None and distance is not None
        
        if has_lead:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')
                
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_decel
            else:
                mode = 'follow'
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
                acceleration_cmd = self.pid_distance.compute(distance_error, dt)
                # Reset speed PID when switching modes? Usually good practice.
                self.pid_speed.reset()
        else:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            self.pid_distance.reset()
            
        # Apply constraints
        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        
        return acceleration_cmd, mode, distance_error

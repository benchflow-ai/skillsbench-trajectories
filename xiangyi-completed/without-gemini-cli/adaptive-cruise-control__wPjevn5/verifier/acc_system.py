from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # PID controllers will be set from outside or initialized here?
        # The prompt says: "Constructor: __init__(self, config) where config is nested dict from vehicle_params.yaml"
        # The prompt also says: "Read PID gains from tuning_results.yaml file at runtime." -> This implies simulation.py does it.
        # But acc_system needs the PID instances.
        # I'll initialize them with placeholders or pass them in?
        # "Method: compute(...) returns tuple"
        # I should probably instantiate PIDs inside __init__ using values from config if available, 
        # but the prompt says simulation.py reads tuning_results.yaml.
        # So I'll assume the config passed to __init__ ALREADY contains the tuned PID values 
        # (merged from vehicle_params and tuning_results).
        
        pid_speed_conf = config.get('pid_speed', {'kp': 0, 'ki': 0, 'kd': 0})
        pid_dist_conf = config.get('pid_distance', {'kp': 0, 'ki': 0, 'kd': 0})
        
        self.pid_speed = PIDController(pid_speed_conf['kp'], pid_speed_conf['ki'], pid_speed_conf['kd'])
        self.pid_distance = PIDController(pid_dist_conf['kp'], pid_dist_conf['ki'], pid_dist_conf['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        accel_cmd = 0.0
        distance_error = None
        
        if lead_speed is None:
            mode = 'cruise'
            # Speed control
            error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
            # Reset distance PID integrator when not in use to avoid windup?
            self.pid_distance.reset()
            
        else:
            # Lead vehicle detected
            # Calculate TTC
            ttc = float('inf')
            rel_speed = ego_speed - lead_speed # positive if closing in
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc:
                mode = 'emergency'
                accel_cmd = self.max_decel # Full brake
                # Reset PIDs
                self.pid_speed.reset()
                self.pid_distance.reset()
                
                # Calculate distance error for logging purposes
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
                
            else:
                mode = 'follow'
                # Distance control
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance
                
                # PID on distance error
                # If distance > desired, error > 0 -> accelerate (positive output)
                # If distance < desired, error < 0 -> decelerate (negative output)
                accel_cmd = self.pid_distance.compute(distance_error, dt)
                
                # Reset speed PID
                self.pid_speed.reset()

        # Clamp acceleration
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        
        return accel_cmd, mode, distance_error

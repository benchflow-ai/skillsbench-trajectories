from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.acc_settings = config['acc_settings']
        self.vehicle_params = config['vehicle']
        
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
        
        # Check if lead vehicle is present
        lead_present = lead_speed is not None and distance is not None
        
        if not lead_present:
            mode = 'cruise'
            error = self.acc_settings['set_speed'] - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
        else:
            # Calculate TTC
            rel_speed = ego_speed - lead_speed
            ttc = distance / rel_speed if rel_speed > 0 else float('inf')
            
            if ttc < self.acc_settings['emergency_ttc_threshold']:
                mode = 'emergency'
                accel_cmd = self.vehicle_params['max_deceleration']
            else:
                mode = 'follow'
                safe_dist = ego_speed * self.acc_settings['time_headway'] + self.acc_settings['min_distance']
                distance_error = distance - safe_dist
                accel_cmd = self.pid_distance.compute(distance_error, dt)
                
        # Clamp acceleration
        accel_cmd = max(self.vehicle_params['max_deceleration'], 
                       min(accel_cmd, self.vehicle_params['max_acceleration']))
        
        return accel_cmd, mode, distance_error

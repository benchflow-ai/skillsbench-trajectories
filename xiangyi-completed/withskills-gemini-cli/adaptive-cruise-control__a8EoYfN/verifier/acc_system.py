import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_cfg = config['acc_settings']
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.min_gap = acc_cfg['min_distance']
        self.emergency_ttc_threshold = acc_cfg['emergency_ttc_threshold']
        
        veh_cfg = config['vehicle']
        self.max_accel = veh_cfg['max_acceleration']
        self.max_decel = veh_cfg['max_deceleration']
        
        # We will use two PID controllers, but they need gains from tuning_results.yaml at runtime in simulation.py.
        # However, the class itself needs to manage them. 
        # Actually, the example says constructor takes config from vehicle_params.yaml.
        # But simulation.py reads gains from tuning_results.yaml.
        # I'll initialize them with some defaults or placeholder and they can be updated or passed in.
        # Re-reading: "AdaptiveCruiseControl Constructor: __init__(self, config) where config is nested dict from vehicle_params.yaml"
        # and "simulation.py: Read PID gains from tuning_results.yaml file at runtime."
        # This implies AdaptiveCruiseControl might need another way to set gains or I should pass them in.
        # Let's add a method to set gains or just initialize them in simulation.py and pass to ACC if I can.
        # But the spec says constructor takes config from vehicle_params.yaml.
        
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

    def update_gains(self, speed_gains, distance_gains):
        self.pid_speed.kp = speed_gains['kp']
        self.pid_speed.ki = speed_gains['ki']
        self.pid_speed.kd = speed_gains['kd']
        
        self.pid_distance.kp = distance_gains['kp']
        self.pid_distance.ki = distance_gains['ki']
        self.pid_distance.kd = distance_gains['kd']

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        ttc = None
        distance_error = None
        
        lead_present = lead_speed is not None and not math.isnan(lead_speed)
        
        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
        else:
            mode = 'cruise'

        if mode == 'cruise':
            error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(error, dt)
            distance_error = None
            self.pid_distance.reset() # Keep distance PID ready
        elif mode == 'emergency':
            acceleration_cmd = self.max_decel
            desired_distance = ego_speed * self.time_headway + self.min_gap
            distance_error = distance - desired_distance
            self.pid_speed.reset()
            self.pid_distance.reset()
        else: # follow
            desired_distance = ego_speed * self.time_headway + self.min_gap
            distance_error = distance - desired_distance
            
            accel_dist = self.pid_distance.compute(distance_error, dt)
            
            speed_error = self.set_speed - ego_speed
            # Compute speed accel but maybe don't update its state if we are distance limited?
            # For simplicity, let's just compute both but keep gains balanced.
            # Actually, to be safe, let's compute them and if we use dist, we should probably 
            # prevent speed PID from winding up.
            accel_speed = self.pid_speed.compute(speed_error, dt)
            
            if accel_dist < accel_speed:
                acceleration_cmd = accel_dist
                # To prevent speed PID windup, we can cap its integral or reset it.
                # But a simple way is to just use the min.
            else:
                acceleration_cmd = accel_speed

        # Clamp acceleration
        acceleration_cmd = max(self.max_decel, min(acceleration_cmd, self.max_accel))
        
        return acceleration_cmd, mode, distance_error

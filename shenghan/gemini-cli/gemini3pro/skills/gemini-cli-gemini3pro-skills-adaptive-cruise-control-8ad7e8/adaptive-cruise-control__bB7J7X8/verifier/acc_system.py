from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize controllers with dummy values, will be updated from tuning_results usually
        # But here we initialize with what's in config (default) or they might be updated later
        # The prompt says simulation.py reads tuning_results. 
        # But acc_system is initialized with config. 
        # I will assume config contains the PID gains or I'll provide methods to update them.
        # Actually, simulation.py will inject the tuned gains into the config or update the controller.
        
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
        self.pid_speed.reset()
        
        self.pid_distance.kp = distance_gains['kp']
        self.pid_distance.ki = distance_gains['ki']
        self.pid_distance.kd = distance_gains['kd']
        self.pid_distance.reset()

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        accel_cmd = 0.0
        distance_error = None
        
        # Check for valid lead vehicle data
        has_lead = lead_speed is not None and distance is not None and str(lead_speed).lower() != 'nan' and str(distance).lower() != 'nan'

        if not has_lead:
            mode = 'cruise'
            # Speed control
            error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
        else:
            # Distance control logic
            # Calculate TTC
            # TTC is technically distance / relative_speed (closing speed)
            # relative_speed = ego_speed - lead_speed
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0.001: # Avoid division by zero, and only care if closing
                ttc = distance / rel_speed
            else:
                ttc = float('inf')

            if ttc < self.ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
            
            # Target distance
            safe_distance = self.min_distance + self.time_headway * ego_speed
            
            # Error definition:
            # If distance > safe_distance, we want to speed up (accel > 0) -> error > 0
            # If distance < safe_distance, we want to slow down (accel < 0) -> error < 0
            error = distance - safe_distance
            distance_error = error
            
            accel_cmd = self.pid_distance.compute(error, dt)

            # Optional: If in follow mode, but speed is way above set_speed, should we cap it?
            # Standard ACC often takes min(speed_accel, dist_accel).
            # But strictly following prompt "Mode selection":
            # If I am in follow mode, I use distance PID. 
            # If distance is huge (far away), PID might ask for huge accel. 
            # I should probably limit it so we don't exceed set_speed?
            # Or assume the "simulated driver" obeys the speed limit? 
            # Let's add a check: if acceleration would push us over set_speed significantly?
            # For now, let's stick to pure PID output but clamped by vehicle physical limits.
            # However, if target is far, we shouldn't exceed set_speed.
            # Let's verify this behavior. Ideally, if distance is large, we shouldn't accelerate past set_speed.
            # So:
            speed_error = self.set_speed - ego_speed
            speed_accel = self.pid_speed.compute(speed_error, dt) 
            # Note: calling compute updates integral. If we don't use it, we shouldn't call it, or we should handle state carefully.
            # But simpler:
            if accel_cmd > speed_accel:
                 accel_cmd = speed_accel
            # This implements min(dist_cmd, speed_cmd) which is safer and standard.
            # But mode remains 'follow' or 'emergency'.

        # Clamp acceleration
        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        
        return accel_cmd, mode, distance_error

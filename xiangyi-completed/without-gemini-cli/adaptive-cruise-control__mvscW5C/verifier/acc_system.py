from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc = config['acc_settings']['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PIDs with config values
        speed_gains = config.get('pid_speed', {'kp': 0.1, 'ki': 0.0, 'kd': 0.0})
        dist_gains = config.get('pid_distance', {'kp': 0.1, 'ki': 0.0, 'kd': 0.0})
        
        self.speed_pid = PIDController(speed_gains['kp'], speed_gains['ki'], speed_gains['kd'])
        self.distance_pid = PIDController(dist_gains['kp'], dist_gains['ki'], dist_gains['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        acc_cmd = 0.0
        mode = 'cruise'
        dist_err = None # Default to None if not relevant, or 0.0? CSV example shows empty for cruise. 
                        # But return type says tuple (acc, mode, dist_error). 
                        # In CSV example: "distance_error" column is empty for cruise. 
                        # I'll return None and handle it in simulation.
        
        # Determine Mode
        # If no lead vehicle (lead_speed is None or distance is None), Cruise.
        if lead_speed is None or distance is None or pd_isna(lead_speed) or pd_isna(distance):
            mode = 'cruise'
        else:
            # Check TTC
            # TTC = distance / (ego - lead)
            rel_speed = ego_speed - lead_speed
            ttc = float('inf')
            if rel_speed > 0.0001: # Closing in
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc:
                mode = 'emergency'
            else:
                mode = 'follow'
        
        # Calculate Control
        if mode == 'cruise':
            # Speed Control
            # Target: set_speed
            # Error = target - current (positive error => accelerate)
            error = self.set_speed - ego_speed
            acc_cmd = self.speed_pid.compute(error, dt)
            dist_err = None
            
        elif mode == 'follow':
            # Distance Control
            # Desired Distance = min_dist + headway * ego_speed
            # Error = Actual - Desired (Positive error means we are too far, accelerate)
            
            desired_distance = self.min_distance + self.time_headway * ego_speed
            dist_err = distance - desired_distance
            
            acc_cmd = self.distance_pid.compute(dist_err, dt)

            # Prevent overshooting set_speed while following
            # Simple P-control limit based on speed error
            # We don't run the full speed_pid.compute() to avoid integral windup during following
            speed_error = self.set_speed - ego_speed
            acc_speed_limit = self.speed_pid.kp * speed_error
            
            # Allow decelerating more than the limit, but not accelerating more
            # If acc_speed_limit is negative (overspeed), we must decel at least that much?
            # No, if overspeed, acc_speed_limit is negative. acc_cmd should be min.
            
            acc_cmd = min(acc_cmd, acc_speed_limit)

            
        elif mode == 'emergency':
            # Emergency braking
            acc_cmd = self.max_decel # Full brake
            desired_distance = self.min_distance + self.time_headway * ego_speed
            dist_err = distance - desired_distance
            # In emergency, we might just override acc_cmd.
            # PID state might need reset or just ignored.
        
        # Apply Limits
        acc_cmd = max(self.max_decel, min(self.max_accel, acc_cmd))
        
        return acc_cmd, mode, dist_err

def pd_isna(obj):
    # Simple check for nan/None without pandas dependency inside class if possible, 
    # but I'll import pandas in simulation. For here:
    return obj is None or (isinstance(obj, float) and obj != obj)

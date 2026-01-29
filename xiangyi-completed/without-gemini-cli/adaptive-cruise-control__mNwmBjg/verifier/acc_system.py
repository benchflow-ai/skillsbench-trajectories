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
        
        # Initialize PIDs with dummy values; they will be updated before simulation if needed
        # But typically they are passed in config. 
        # The prompt says: "Constructor: __init__(self, config) where config is nested dict from vehicle_params.yaml"
        # And "tuning_results.yaml" will supply the values at runtime for simulation.py.
        # But acc_system might be initialized with vehicle_params which has default values.
        # I will use whatever is in config.
        
        ps = config['pid_speed']
        self.pid_speed = PIDController(ps['kp'], ps['ki'], ps['kd'])
        
        pd = config['pid_distance']
        self.pid_distance = PIDController(pd['kp'], pd['ki'], pd['kd'])

    def update_gains(self, pid_type, kp, ki, kd):
        if pid_type == 'speed':
            self.pid_speed.kp = kp
            self.pid_speed.ki = ki
            self.pid_speed.kd = kd
            self.pid_speed.reset()
        elif pid_type == 'distance':
            self.pid_distance.kp = kp
            self.pid_distance.ki = ki
            self.pid_distance.kd = kd
            self.pid_distance.reset()

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Returns: (acceleration_cmd, mode, distance_error)
        """
        mode = 'cruise'
        accel_cmd = 0.0
        dist_error = 0.0 # Relevant for follow mode
        
        # Check for lead vehicle
        has_lead = (lead_speed is not None) and (distance is not None)
        
        if not has_lead:
            mode = 'cruise'
            # Speed Control
            error = self.set_speed - ego_speed
            # If we switch modes, we might want to reset the unused PID, 
            # but simple switching is often okay. 
            # Ideally reset distance PID integral when not in use.
            self.pid_distance.reset() 
            accel_cmd = self.pid_speed.compute(error, dt)
            
        else:
            # Calculate TTC
            # TTC = distance / relative_speed (if closing)
            # relative_speed = ego_speed - lead_speed (positive means closing in)
            rel_speed = ego_speed - lead_speed
            ttc = float('inf')
            if rel_speed > 0.001: # Avoiding div by zero
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc:
                mode = 'emergency'
                accel_cmd = self.max_decel # Max braking
                self.pid_speed.reset()
                self.pid_distance.reset()
                # For reporting, calculate distance error even in emergency
                desired_dist = self.min_distance + self.time_headway * ego_speed
                dist_error = distance - desired_dist
                
            else:
                mode = 'follow'
                # Distance Control
                # desired_distance = d0 + t_gap * v_ego
                desired_dist = self.min_distance + self.time_headway * ego_speed
                
                # Error definition: 
                dist_error = distance - desired_dist
                
                # Min-select strategy:
                # 1. Acceleration to maintain distance
                accel_dist = self.pid_distance.compute(dist_error, dt)
                
                # 2. Acceleration to maintain set_speed (Speed limit)
                # We reuse pid_speed controller but need to be careful if it had integral (it doesn't currently)
                # To be safe/clean, we compute it.
                speed_error = self.set_speed - ego_speed
                accel_speed = self.pid_speed.compute(speed_error, dt)
                
                # Take the more restrictive (lower) acceleration
                accel_cmd = min(accel_dist, accel_speed)

        # Clamp acceleration
        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        
        return accel_cmd, mode, dist_error

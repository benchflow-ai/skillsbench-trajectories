from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.acc_settings = config['acc_settings']
        self.vehicle_params = config['vehicle']
        
        # Initialize PIDs
        # Gains will be updated from tuning_results.yaml at runtime in simulation.py, 
        # but here we initialize with defaults or whatever is passed in config if available.
        # The prompt says simulation.py reads tuning_results.yaml. 
        # So we might need a method to update gains or pass them in config.
        # Assuming config['pid_speed'] and config['pid_distance'] are populated.
        
        speed_gains = config.get('pid_speed', {'kp': 0, 'ki': 0, 'kd': 0})
        dist_gains = config.get('pid_distance', {'kp': 0, 'ki': 0, 'kd': 0})
        
        self.pid_speed = PIDController(speed_gains['kp'], speed_gains['ki'], speed_gains['kd'])
        self.pid_distance = PIDController(dist_gains['kp'], dist_gains['ki'], dist_gains['kd'])

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
        mode = 'cruise'
        acceleration_cmd = 0.0
        distance_error = None
        ttc = None

        # Determine if lead vehicle is present (valid distance and lead_speed)
        # In sensor_data.csv, missing values are empty. In python, likely None or NaN.
        import math
        lead_present = False
        if distance is not None and not math.isnan(distance) and lead_speed is not None and not math.isnan(lead_speed):
            lead_present = True

        if lead_present:
            # Calculate TTC
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf') # Not approaching or moving away

            # Determine Mode
            if ttc < self.acc_settings['emergency_ttc_threshold']:
                mode = 'emergency'
            else:
                mode = 'follow'
        else:
            mode = 'cruise'
            ttc = None

        # Control Logic
        if mode == 'cruise':
            # Speed Control
            target_speed = self.acc_settings['set_speed']
            speed_error = target_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(speed_error, dt)
            
            # Reset distance PID integrator to avoid windup when not in use
            self.pid_distance.reset()

        elif mode == 'follow':
            # Distance Control
            # Safe distance = time_headway * ego_speed + min_distance
            safe_distance = self.acc_settings['time_headway'] * ego_speed + self.acc_settings['min_distance']
            
            # Error = Actual - Desired. 
            # If Actual > Desired (Positive), we are safe/far, we can accelerate? 
            # Wait, if we are far, we want to speed up to close the gap? 
            # Or do we just want to maintain distance?
            # Standard ACC: Try to match speed and maintain distance.
            # If we use a single PID on distance error:
            # Positive error (distance > safe) -> Positive output (Accel)
            # Negative error (distance < safe) -> Negative output (Decel)
            distance_error = distance - safe_distance
            acceleration_cmd = self.pid_distance.compute(distance_error, dt)
            
            # Reset speed PID integrator? Maybe not, maybe we switch back. 
            # But usually separate controllers.
            self.pid_speed.reset()

        elif mode == 'emergency':
            # Emergency Braking
            acceleration_cmd = self.vehicle_params['max_deceleration']
            
            # Calculate distance error for reporting even in emergency
            safe_distance = self.acc_settings['time_headway'] * ego_speed + self.acc_settings['min_distance']
            distance_error = distance - safe_distance
            
            self.pid_speed.reset()
            self.pid_distance.reset()

        # Clamp Acceleration
        acceleration_cmd = max(self.vehicle_params['max_deceleration'], 
                               min(acceleration_cmd, self.vehicle_params['max_acceleration']))

        return acceleration_cmd, mode, distance_error, ttc

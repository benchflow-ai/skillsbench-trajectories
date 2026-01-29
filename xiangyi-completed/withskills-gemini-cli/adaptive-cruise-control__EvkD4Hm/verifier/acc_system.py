from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # Acceleration limits
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

        # PID Controllers (gains will be set/updated from tuning_results.yaml later)
        # Default/Placeholder values are initialized here, but should be updated
        self.speed_controller = PIDController(
            kp=config.get('pid_speed', {}).get('kp', 0.1),
            ki=config.get('pid_speed', {}).get('ki', 0.01),
            kd=config.get('pid_speed', {}).get('kd', 0.0),
            output_min=self.max_decel,
            output_max=self.max_accel
        )
        
        self.distance_controller = PIDController(
            kp=config.get('pid_distance', {}).get('kp', 0.1),
            ki=config.get('pid_distance', {}).get('ki', 0.01),
            kd=config.get('pid_distance', {}).get('kd', 0.0),
            output_min=self.max_decel,
            output_max=self.max_accel
        )

    def update_gains(self, speed_gains, distance_gains):
        self.speed_controller.kp = speed_gains['kp']
        self.speed_controller.ki = speed_gains['ki']
        self.speed_controller.kd = speed_gains['kd']
        
        self.distance_controller.kp = distance_gains['kp']
        self.distance_controller.ki = distance_gains['ki']
        self.distance_controller.kd = distance_gains['kd']

    def calculate_safe_distance(self, speed):
        return speed * self.time_headway + self.min_distance

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on sensor inputs.
        
        Returns:
            acceleration_cmd (float)
            mode (str): 'cruise', 'follow', 'emergency'
            distance_error (float or None)
        """
        mode = 'cruise'
        distance_error = None
        
        # Determine mode
        if lead_speed is None or distance is None or pd.isna(distance):
            mode = 'cruise'
        else:
            # Check for emergency
            ttc = None
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0: # Approaching
                ttc = distance / relative_speed
                
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'

        # Compute control based on mode
        acceleration_cmd = 0.0

        if mode == 'cruise':
            # Speed control: Maintain set_speed
            error = self.set_speed - ego_speed
            # Reset distance controller to prevent windup
            self.distance_controller.reset()
            acceleration_cmd = self.speed_controller.compute(error, dt)
            
        elif mode == 'follow':
            # Distance control: Maintain safe following distance
            target_distance = self.calculate_safe_distance(ego_speed)
            # Error is (Actual - Target) so positive error means we are too far, need to speed up?
            # PID is usually Kp * error.
            # If distance > target, error > 0. We want to speed up (accel > 0).
            # So error = distance - target_distance seems correct for positive Kp.
            
            # Wait, standard PID: output = Kp * (setpoint - measured).
            # Here "measured" is distance. "setpoint" is target_distance.
            # If setpoint > measured (too close), we want to slow down (accel < 0).
            # So error = target_distance - distance results in positive error when too close.
            # With positive Kp, that gives positive accel -> crash.
            # So for distance control, either use negative gains or flip error.
            # Usually: error = distance - target_distance.
            # If distance (100) > target (50), error = +50. We want accel > 0. Correct.
            # If distance (10) < target (50), error = -40. We want accel < 0. Correct.
            
            error = distance - target_distance
            distance_error = error
            
            # Reset speed controller? Maybe not strict requirement but good practice to avoid windup if we switch back
            self.speed_controller.reset() 
            acceleration_cmd = self.distance_controller.compute(error, dt)

        elif mode == 'emergency':
            # Max braking
            acceleration_cmd = self.max_decel
            distance_error = distance - self.calculate_safe_distance(ego_speed) # Calculate for logging
            
            # Reset controllers
            self.speed_controller.reset()
            self.distance_controller.reset()

        return acceleration_cmd, mode, distance_error

import pandas as pd # Needed for isna check

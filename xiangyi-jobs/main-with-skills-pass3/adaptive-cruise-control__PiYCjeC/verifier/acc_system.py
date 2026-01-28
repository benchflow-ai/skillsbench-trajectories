from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.acc_settings = config['acc_settings']
        self.vehicle_params = config['vehicle']
        self.last_mode = None
        
        # Initialize Speed PID
        speed_pid_config = config.get('pid_speed', {})
        self.speed_pid = PIDController(
            kp=speed_pid_config.get('kp', 0.1),
            ki=speed_pid_config.get('ki', 0.0),
            kd=speed_pid_config.get('kd', 0.0),
            output_min=self.vehicle_params['max_deceleration'],
            output_max=self.vehicle_params['max_acceleration']
        )
        
        # Initialize Distance PID
        dist_pid_config = config.get('pid_distance', {})
        self.distance_pid = PIDController(
            kp=dist_pid_config.get('kp', 0.1),
            ki=dist_pid_config.get('ki', 0.0),
            kd=dist_pid_config.get('kd', 0.0),
            output_min=self.vehicle_params['max_deceleration'],
            output_max=self.vehicle_params['max_acceleration']
        )

    def calculate_safe_distance(self, speed):
        """Calculate safe following distance based on current speed."""
        return speed * self.acc_settings['time_headway'] + self.acc_settings['min_distance']

    def calculate_ttc(self, distance, ego_speed, lead_speed):
        """Calculate time to collision."""
        if lead_speed is None:
            return None
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None
        return distance / relative_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command.
        
        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s) or None
            distance: Distance to lead vehicle (m) or None
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        ttc = self.calculate_ttc(distance, ego_speed, lead_speed)
        
        # Determine mode
        if lead_speed is None or distance is None:
            mode = 'cruise'
        elif ttc is not None and ttc < self.acc_settings['emergency_ttc_threshold']:
            mode = 'emergency'
        else:
            mode = 'follow'

        # Mode initialization detection
        if mode != self.last_mode:
            if mode == 'follow':
                # Initialize distance PID to avoid kick
                safe_dist = self.calculate_safe_distance(ego_speed)
                dist_error = distance - safe_dist
                self.distance_pid.initialize(dist_error)
                # Also ensure speed PID is clean? 
                # Speed PID might have integral windup from cruise?
                # Actually, if we were in cruise, speed PID is active.
                # If we switch to follow, we CONTINUE using speed PID as a limiter.
                # So we shouldn't reset speed PID usually.
                # But distance PID needs initialization.
            elif mode == 'cruise':
                # Switching back to cruise.
                # Reset distance PID
                self.distance_pid.reset()
                # Speed PID should be smooth.
                target_speed = self.acc_settings['set_speed']
                speed_error = target_speed - ego_speed
                # self.speed_pid.initialize(speed_error) # Optional, but continuity is better
        
        self.last_mode = mode
        distance_error = None
        
        if mode == 'cruise':
            # Speed control
            target_speed = self.acc_settings['set_speed']
            error = target_speed - ego_speed
            accel_cmd = self.speed_pid.compute(error, dt)
            
        elif mode == 'emergency':
            # Max braking
            accel_cmd = self.vehicle_params['max_deceleration']
            self.speed_pid.reset()
            self.distance_pid.reset()
            # Calculate distance error for logging
            if distance is not None:
                safe_dist = self.calculate_safe_distance(ego_speed)
                distance_error = distance - safe_dist
            
        elif mode == 'follow':
            # Parallel Control Architecture
            
            # 1. Distance Control
            safe_dist = self.calculate_safe_distance(ego_speed)
            dist_error = distance - safe_dist
            distance_error = dist_error
            dist_accel = self.distance_pid.compute(dist_error, dt)
            
            # 2. Speed Control (Limiter)
            target_speed = self.acc_settings['set_speed']
            speed_error = target_speed - ego_speed
            speed_accel = self.speed_pid.compute(speed_error, dt)
            
            # Take the minimum acceleration (most conservative)
            accel_cmd = min(dist_accel, speed_accel)

        return accel_cmd, mode, distance_error

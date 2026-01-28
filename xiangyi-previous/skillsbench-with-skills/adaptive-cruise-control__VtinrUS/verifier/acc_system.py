"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control with speed and distance control modes."""
    
    def __init__(self, config):
        """
        Initialize ACC system with configuration.
        
        Args:
            config: Nested dict from vehicle_params.yaml
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']
        
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # Output limits for anti-windup
        self.output_limits = (self.max_deceleration, self.max_acceleration)
        
        # PID controllers with output limits for anti-windup
        speed_pid = config.get('pid_speed', {'kp': 0.5, 'ki': 0.02, 'kd': 0.1})
        dist_pid = config.get('pid_distance', {'kp': 0.3, 'ki': 0.01, 'kd': 1.5})
        
        self.speed_controller = PIDController(
            speed_pid['kp'], speed_pid['ki'], speed_pid['kd'],
            output_limits=self.output_limits
        )
        self.distance_controller = PIDController(
            dist_pid['kp'], dist_pid['ki'], dist_pid['kd'],
            output_limits=self.output_limits
        )
        
        self.prev_mode = 'cruise'
    
    def set_pid_gains(self, speed_gains, distance_gains):
        """
        Update PID gains for both controllers.
        """
        self.speed_controller = PIDController(
            speed_gains['kp'], speed_gains['ki'], speed_gains['kd'],
            output_limits=self.output_limits
        )
        self.distance_controller = PIDController(
            distance_gains['kp'], distance_gains['ki'], distance_gains['kd'],
            output_limits=self.output_limits
        )
    
    def compute_desired_distance(self, ego_speed):
        """Compute desired following distance based on time headway."""
        return self.min_distance + self.time_headway * ego_speed
    
    def compute_ttc(self, ego_speed, lead_speed, distance):
        """Compute Time-To-Collision."""
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return float('inf')
        return distance / relative_speed
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control command.
        
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        # Cruise mode - no lead vehicle detected
        if lead_speed is None or distance is None:
            # Reset distance controller when switching to cruise
            if self.prev_mode != 'cruise':
                self.distance_controller.reset()
                self.speed_controller.reset()
            
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            
            # Clamp acceleration
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            self.prev_mode = 'cruise'
            return (accel_cmd, 'cruise', None)
        
        # Calculate TTC for emergency detection
        ttc = self.compute_ttc(ego_speed, lead_speed, distance)
        
        # Emergency mode - TTC below threshold
        if ttc < self.emergency_ttc_threshold:
            desired_dist = self.compute_desired_distance(ego_speed)
            distance_error = distance - desired_dist
            accel_cmd = self.max_deceleration
            self.prev_mode = 'emergency'
            return (accel_cmd, 'emergency', distance_error)
        
        # Reset controllers when switching from cruise to follow
        if self.prev_mode == 'cruise':
            self.distance_controller.reset()
            self.speed_controller.reset()
        
        # Follow mode - maintain safe following distance
        desired_distance = self.compute_desired_distance(ego_speed)
        distance_error = distance - desired_distance
        
        # Distance control
        dist_accel = self.distance_controller.compute(distance_error, dt)
        
        # Speed matching with lead vehicle (capped at set_speed)
        target_speed = min(lead_speed, self.set_speed)
        speed_error = target_speed - ego_speed
        speed_accel = self.speed_controller.compute(speed_error, dt)
        
        # Combine controls based on distance error
        if distance_error < -5:  # Much too close
            accel_cmd = min(dist_accel, speed_accel, -2.0)
        elif distance_error < 0:  # Slightly too close
            accel_cmd = 0.7 * dist_accel + 0.3 * speed_accel
        elif distance_error > 10:  # Far behind
            accel_cmd = 0.5 * dist_accel + 0.5 * speed_accel
        else:  # Good distance range
            accel_cmd = 0.4 * dist_accel + 0.6 * speed_accel
        
        # Clamp acceleration
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
        
        self.prev_mode = 'follow'
        return (accel_cmd, 'follow', distance_error)

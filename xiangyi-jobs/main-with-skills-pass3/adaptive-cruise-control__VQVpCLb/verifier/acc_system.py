import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with PID-based speed and distance control."""
    
    def __init__(self, config):
        """Initialize ACC system.
        
        Args:
            config: Configuration dict from vehicle_params.yaml
        """
        self.config = config
        
        # Vehicle parameters
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # PID controllers for speed and distance
        speed_gains = config['pid_speed']
        distance_gains = config['pid_distance']
        
        self.speed_controller = PIDController(
            kp=speed_gains['kp'],
            ki=speed_gains['ki'],
            kd=speed_gains['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel
        )
        
        self.distance_controller = PIDController(
            kp=distance_gains['kp'],
            ki=distance_gains['ki'],
            kd=distance_gains['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel
        )
    
    def _calculate_safe_distance(self, speed):
        """Calculate safe following distance based on speed.
        
        Args:
            speed: Current vehicle speed (m/s)
            
        Returns:
            Safe following distance (meters)
        """
        return speed * self.time_headway + self.min_distance
    
    def _calculate_ttc(self, distance, ego_speed, lead_speed):
        """Calculate time-to-collision.
        
        Args:
            distance: Current distance to lead vehicle (m)
            ego_speed: Ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            
        Returns:
            Time-to-collision in seconds, or None if not approaching
        """
        relative_speed = ego_speed - lead_speed
        
        if relative_speed <= 0:
            return None  # Not approaching
        
        if distance <= 0:
            return 0.0  # Already colliding
        
        return distance / relative_speed
    
    def _determine_mode(self, lead_present, ttc):
        """Determine ACC operating mode.
        
        Args:
            lead_present: Whether a lead vehicle is detected
            ttc: Time-to-collision value
            
        Returns:
            Mode string: 'cruise', 'follow', or 'emergency'
        """
        if not lead_present:
            return 'cruise'
        
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            return 'emergency'
        
        return 'follow'
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command for ACC.
        
        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step (seconds)
            
        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration (m/s^2)
            - mode: Operating mode ('cruise', 'follow', 'emergency')
            - distance_error: Distance error in follow mode, None otherwise
        """
        # Determine if lead vehicle is present
        lead_present = (lead_speed is not None and distance is not None)
        
        # Calculate TTC if lead vehicle present
        ttc = None
        distance_error = None
        
        if lead_present:
            ttc = self._calculate_ttc(distance, ego_speed, lead_speed)
        
        # Determine mode
        mode = self._determine_mode(lead_present, ttc)
        
        # Compute acceleration based on mode
        if mode == 'cruise':
            # Cruise mode: maintain set speed
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
        
        elif mode == 'follow':
            # Follow mode: maintain safe distance
            safe_distance = self._calculate_safe_distance(ego_speed)
            distance_error = safe_distance - distance
            
            # Use distance controller for following
            accel_cmd = self.distance_controller.compute(distance_error, dt)
        
        elif mode == 'emergency':
            # Emergency mode: maximum deceleration
            accel_cmd = self.max_decel
        
        # Clamp acceleration to physical limits
        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        
        return accel_cmd, mode, distance_error

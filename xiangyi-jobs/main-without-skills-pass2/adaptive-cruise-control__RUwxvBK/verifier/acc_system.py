"""
Adaptive Cruise Control System
"""

from pid_controller import PIDController
from typing import Tuple, Optional


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed in cruise mode
    and adjusts speed to maintain safe following distance when a lead vehicle
    is detected.
    """
    
    def __init__(self, config: dict):
        """
        Initialize ACC system with configuration.
        
        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - vehicle: mass, max_acceleration, max_deceleration, drag_coefficient
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']
        
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # PID controllers
        self.speed_pid = PIDController(
            kp=config['pid_speed']['kp'],
            ki=config['pid_speed']['ki'],
            kd=config['pid_speed']['kd']
        )
        
        self.distance_pid = PIDController(
            kp=config['pid_distance']['kp'],
            ki=config['pid_distance']['ki'],
            kd=config['pid_distance']['kd']
        )
        
        self.current_mode = 'cruise'
    
    def calculate_safe_distance(self, ego_speed: float) -> float:
        """
        Calculate safe following distance based on current speed.
        
        Safe distance = max(min_distance, time_headway * ego_speed)
        
        Args:
            ego_speed: Current ego vehicle speed in m/s
            
        Returns:
            Safe following distance in meters
        """
        return max(self.min_distance, self.time_headway * ego_speed)
    
    def calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """
        Calculate Time-To-Collision.
        
        TTC = distance / (ego_speed - lead_speed) when closing
        
        Args:
            ego_speed: Ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s
            distance: Distance to lead vehicle in meters
            
        Returns:
            TTC in seconds, or None if not closing
        """
        relative_speed = ego_speed - lead_speed
        
        if relative_speed <= 0:
            # Not closing, no collision risk
            return None
        
        if distance <= 0:
            return 0.0
        
        return distance / relative_speed
    
    def compute(self, ego_speed: float, lead_speed: Optional[float], 
                distance: Optional[float], dt: float) -> Tuple[float, str, Optional[float]]:
        """
        Compute acceleration command based on current state.
        
        Args:
            ego_speed: Current ego vehicle speed in m/s
            lead_speed: Lead vehicle speed in m/s (None if no lead vehicle)
            distance: Distance to lead vehicle in meters (None if no lead vehicle)
            dt: Time step in seconds
            
        Returns:
            Tuple of (acceleration_cmd, mode, distance_error)
            - acceleration_cmd: Commanded acceleration in m/s^2
            - mode: 'cruise', 'follow', or 'emergency'
            - distance_error: Error from safe distance (None in cruise mode)
        """
        # Check if lead vehicle is present
        if lead_speed is None or distance is None:
            # No lead vehicle - cruise mode
            self.current_mode = 'cruise'
            
            # Speed control to reach set_speed
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
            
            # Reset distance PID when not in use
            self.distance_pid.reset()
            
            # Clamp acceleration
            acceleration_cmd = max(self.max_deceleration, 
                                   min(self.max_acceleration, acceleration_cmd))
            
            return (acceleration_cmd, 'cruise', None)
        
        # Lead vehicle present - check for emergency
        ttc = self.calculate_ttc(ego_speed, lead_speed, distance)
        
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            # Emergency braking
            self.current_mode = 'emergency'
            acceleration_cmd = self.max_deceleration
            
            safe_distance = self.calculate_safe_distance(ego_speed)
            distance_error = distance - safe_distance
            
            return (acceleration_cmd, 'emergency', distance_error)
        
        # Follow mode - maintain safe distance
        self.current_mode = 'follow'
        
        # Calculate safe distance and error
        safe_distance = self.calculate_safe_distance(ego_speed)
        distance_error = distance - safe_distance  # positive = too far, negative = too close
        
        # Calculate desired speed based on lead vehicle and distance error
        # If too close (negative error), we want to go slower than lead
        # If too far (positive error), we can go faster (up to set_speed)
        
        # Target speed based on distance error
        # Use a proportional relationship: adjust target speed based on distance error
        speed_adjustment = distance_error * 0.2  # Convert distance error to speed adjustment
        target_speed = lead_speed + speed_adjustment
        
        # Don't exceed set speed
        target_speed = min(target_speed, self.set_speed)
        # Don't go negative
        target_speed = max(0, target_speed)
        
        # Use speed PID to track target speed
        speed_error = target_speed - ego_speed
        acceleration_cmd = self.speed_pid.compute(speed_error, dt)
        
        # Add distance-based correction for safety
        if distance_error < 0:  # Too close
            # Apply additional braking proportional to how close we are
            distance_correction = self.distance_pid.compute(distance_error, dt)
            acceleration_cmd = min(acceleration_cmd, distance_correction)
        
        # Clamp acceleration
        acceleration_cmd = max(self.max_deceleration, 
                               min(self.max_acceleration, acceleration_cmd))
        
        return (acceleration_cmd, 'follow', distance_error)
    
    def reset(self):
        """
        Reset both PID controllers.
        """
        self.speed_pid.reset()
        self.distance_pid.reset()
        self.current_mode = 'cruise'


if __name__ == "__main__":
    import yaml
    
    # Load config
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create ACC system
    acc = AdaptiveCruiseControl(config)
    
    # Test cruise mode
    accel, mode, dist_err = acc.compute(ego_speed=20.0, lead_speed=None, distance=None, dt=0.1)
    print(f"Cruise mode: accel={accel:.2f}, mode={mode}, dist_err={dist_err}")
    
    # Test follow mode
    accel, mode, dist_err = acc.compute(ego_speed=25.0, lead_speed=20.0, distance=50.0, dt=0.1)
    print(f"Follow mode: accel={accel:.2f}, mode={mode}, dist_err={dist_err:.2f}")
    
    # Test emergency mode
    accel, mode, dist_err = acc.compute(ego_speed=30.0, lead_speed=10.0, distance=30.0, dt=0.1)
    print(f"Emergency mode: accel={accel:.2f}, mode={mode}, dist_err={dist_err:.2f}")
    
    print("ACC System test passed!")

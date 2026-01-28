"""
Adaptive Cruise Control (ACC) System implementation.
Designed for smooth speed and distance control.
"""

from pid_controller import PIDController
from typing import Tuple, Optional


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the ACC system with configuration.
        """
        # Vehicle parameters
        self.mass = config['vehicle']['mass']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        # PID controllers
        speed_gains = config['pid_speed']
        distance_gains = config['pid_distance']
        
        self.speed_pid = PIDController(
            kp=speed_gains['kp'],
            ki=speed_gains['ki'],
            kd=speed_gains['kd']
        )
        self.speed_pid.set_output_limits(self.max_decel, self.max_accel)
        
        self.distance_pid = PIDController(
            kp=distance_gains['kp'],
            ki=distance_gains['ki'],
            kd=distance_gains['kd']
        )
        self.distance_pid.set_output_limits(self.max_decel, self.max_accel)
        
        self._prev_mode = 'cruise'
    
    def _calculate_ttc(self, ego_speed: float, lead_speed: float, distance: float) -> Optional[float]:
        """Calculate Time-To-Collision."""
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0.01:
            return None
        return distance / relative_speed
    
    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate desired following distance."""
        return self.min_distance + self.time_headway * ego_speed
    
    def _clamp_acceleration(self, accel: float) -> float:
        """Clamp acceleration to vehicle limits."""
        return max(self.max_decel, min(self.max_accel, accel))
    
    def compute(self, ego_speed: float, lead_speed: Optional[float], 
                distance: Optional[float], dt: float) -> Tuple[float, str, Optional[float]]:
        """
        Compute the acceleration command.
        """
        if lead_speed is None or distance is None:
            # CRUISE MODE - no lead vehicle
            mode = 'cruise'
            distance_error = None
            
            if self._prev_mode != 'cruise':
                self.distance_pid.reset()
            
            # Speed error
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            
        else:
            # Lead vehicle present
            ttc = self._calculate_ttc(ego_speed, lead_speed, distance)
            desired_distance = self._calculate_desired_distance(ego_speed)
            distance_error = distance - desired_distance
            
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                # EMERGENCY MODE
                mode = 'emergency'
                accel_cmd = self.max_decel
            else:
                # FOLLOW MODE
                mode = 'follow'
                
                if self._prev_mode == 'cruise':
                    self.speed_pid.reset()
                    self.distance_pid.reset()
                
                # Strategy: Control speed to achieve desired distance
                # If distance_error > 0: too far, can speed up
                # If distance_error < 0: too close, must slow down
                
                # Calculate target speed based on distance error and lead speed
                # Use a proportional approach: adjust target speed based on distance error
                relative_speed = ego_speed - lead_speed
                
                # Target speed adjustment based on distance error
                # Positive distance_error -> can go faster than lead
                # Negative distance_error -> must go slower than lead
                speed_adjustment = distance_error * 0.1  # Gain for distance->speed conversion
                
                # Target speed is lead speed plus adjustment, but capped at set_speed
                target_speed = lead_speed + speed_adjustment
                target_speed = max(0, min(target_speed, self.set_speed))
                
                # Speed error relative to target
                speed_error = target_speed - ego_speed
                
                # Use speed PID to track target speed
                accel_cmd = self.speed_pid.compute(speed_error, dt)
                
                # Additional safety for very close distances
                if distance < self.min_distance:
                    # Force deceleration proportional to how close we are
                    safety_decel = (self.min_distance - distance) * 0.5
                    accel_cmd = min(accel_cmd, -safety_decel)
        
        accel_cmd = self._clamp_acceleration(accel_cmd)
        self._prev_mode = mode
        
        return accel_cmd, mode, distance_error
    
    def reset(self):
        """Reset controllers."""
        self.speed_pid.reset()
        self.distance_pid.reset()
        self._prev_mode = 'cruise'

"""
Adaptive Cruise Control (ACC) System Implementation

Implements three control modes: cruise, follow, and emergency.
Uses cascade PID control for speed and distance management.
"""

import math
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or follows lead vehicle.
    
    Modes:
    - 'cruise': No lead vehicle, maintain set speed
    - 'follow': Lead vehicle detected, maintain safe distance
    - 'emergency': TTC below threshold, maximum deceleration
    """
    
    def __init__(self, config):
        """
        Initialize ACC system from configuration.
        
        Args:
            config: Dict with nested structure from vehicle_params.yaml
                    Must contain: acc_settings, control, (pid_gains if provided)
        """
        self.config = config
        
        # Extract ACC settings
        acc_cfg = config['acc_settings']
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.minimum_gap = acc_cfg['minimum_gap']
        self.emergency_ttc_threshold = acc_cfg['emergency_ttc_threshold']
        
        # Extract control settings
        ctrl_cfg = config['control']
        self.accel_min = ctrl_cfg['accel_min']
        self.accel_max = ctrl_cfg['accel_max']
        
        # Initialize PID controllers
        # Will be configured with gains later (from tuning_results.yaml)
        self.speed_pid = None
        self.distance_pid = None
        
    def set_pid_gains(self, speed_gains, distance_gains):
        """
        Set PID controller gains.
        
        Args:
            speed_gains: Dict with keys 'kp', 'ki', 'kd' for speed control
            distance_gains: Dict with keys 'kp', 'ki', 'kd' for distance control
        """
        self.speed_pid = PIDController(
            speed_gains['kp'], speed_gains['ki'], speed_gains['kd'],
            output_limits=(self.accel_min, self.accel_max)
        )
        self.distance_pid = PIDController(
            distance_gains['kp'], distance_gains['ki'], distance_gains['kd']
        )
    
    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command for current state.
        
        Args:
            ego_speed: Current vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s or None)
            distance: Gap to lead vehicle (m or None)
            dt: Time step (s)
            
        Returns:
            Tuple of (acceleration_cmd, mode, distance_error):
                - acceleration_cmd: Acceleration command (m/s²)
                - mode: Control mode string ('cruise', 'follow', 'emergency')
                - distance_error: Distance error for diagnostics (m or None)
        """
        
        # Check for lead vehicle
        has_lead = lead_speed is not None and not math.isnan(lead_speed)
        
        if not has_lead:
            # No lead vehicle: cruise mode
            return self._cruise_mode(ego_speed, dt)
        
        # Check emergency condition: time-to-collision
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)
        
        if ttc < self.emergency_ttc_threshold:
            # Emergency braking
            return self._emergency_mode()
        
        # Follow lead vehicle
        return self._follow_mode(ego_speed, lead_speed, distance, dt)
    
    def _cruise_mode(self, ego_speed, dt):
        """
        Cruise mode: accelerate to and maintain set speed.
        
        Args:
            ego_speed: Current speed (m/s)
            dt: Time step (s)
            
        Returns:
            Tuple (accel_cmd, mode, distance_error)
        """
        # Speed error: setpoint - current
        speed_error = self.set_speed - ego_speed
        
        # Compute acceleration via speed PID
        accel_cmd = self.speed_pid.compute(speed_error, dt)
        
        # Clamp to physical limits
        accel_cmd = max(self.accel_min, min(self.accel_max, accel_cmd))
        
        return accel_cmd, 'cruise', None
    
    def _follow_mode(self, ego_speed, lead_speed, distance, dt):
        """
        Follow mode: maintain safe distance behind lead vehicle.
        
        Uses cascade control: distance error -> desired speed -> acceleration
        
        Args:
            ego_speed: Current speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Gap to lead vehicle (m)
            dt: Time step (s)
            
        Returns:
            Tuple (accel_cmd, mode, distance_error)
        """
        # Calculate desired following distance
        desired_distance = self.time_headway * ego_speed + self.minimum_gap
        
        # Distance error: desired - actual
        distance_error = desired_distance - distance
        
        # Distance PID outputs desired speed adjustment
        # Positive error (gap too small) -> reduce speed
        speed_adjustment = self.distance_pid.compute(distance_error, dt)
        
        # Desired speed: set speed plus adjustment
        desired_speed = self.set_speed + speed_adjustment
        
        # Clamp desired speed to match lead vehicle (can't be faster)
        desired_speed = min(desired_speed, lead_speed + 0.1)  # Small margin
        desired_speed = max(0.0, desired_speed)
        
        # Speed error for main speed PID
        speed_error = desired_speed - ego_speed
        
        # Compute acceleration via speed PID
        accel_cmd = self.speed_pid.compute(speed_error, dt)
        
        # Clamp to physical limits
        accel_cmd = max(self.accel_min, min(self.accel_max, accel_cmd))
        
        return accel_cmd, 'follow', distance_error
    
    def _emergency_mode(self):
        """
        Emergency mode: maximum deceleration.
        
        Returns:
            Tuple (accel_cmd, mode, distance_error)
        """
        # Full brake
        return self.accel_min, 'emergency', None
    
    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """
        Compute time-to-collision.
        
        Args:
            ego_speed: Current speed (m/s)
            lead_speed: Lead speed (m/s)
            distance: Gap to lead vehicle (m)
            
        Returns:
            float: TTC in seconds (inf if moving away or parallel)
        """
        relative_velocity = ego_speed - lead_speed
        
        if relative_velocity <= 0:
            return float('inf')  # Moving away or parallel, safe
        
        return distance / relative_velocity
    
    def reset(self):
        """Reset all controller states."""
        if self.speed_pid:
            self.speed_pid.reset()
        if self.distance_pid:
            self.distance_pid.reset()

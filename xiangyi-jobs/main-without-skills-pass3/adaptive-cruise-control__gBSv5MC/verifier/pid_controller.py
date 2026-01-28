"""
PID Controller implementation for Adaptive Cruise Control system.
Includes anti-windup protection.
"""

class PIDController:
    """
    A PID controller with anti-windup protection.
    """
    
    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize the PID controller with given gains.
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._integral = 0.0
        self._prev_error = None
        self._output_min = -100.0
        self._output_max = 100.0
    
    def set_output_limits(self, min_val: float, max_val: float):
        """
        Set output limits for anti-windup.
        """
        self._output_min = min_val
        self._output_max = max_val
    
    def reset(self):
        """
        Reset the controller state.
        """
        self._integral = 0.0
        self._prev_error = None
    
    def compute(self, error: float, dt: float) -> float:
        """
        Compute the control output with anti-windup.
        """
        # Proportional term
        p_term = self.kp * error
        
        # Derivative term (compute before updating integral)
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt
        
        # Compute output without integral to check for saturation
        output_pd = p_term + d_term
        
        # Conditional integration (anti-windup)
        # Only integrate if:
        # 1. Output is not saturated, OR
        # 2. Integration would reduce the saturation
        if self._output_min < output_pd < self._output_max:
            # Not saturated, integrate normally
            self._integral += error * dt
        elif output_pd >= self._output_max and error < 0:
            # Saturated high but error is negative (would reduce)
            self._integral += error * dt
        elif output_pd <= self._output_min and error > 0:
            # Saturated low but error is positive (would reduce)
            self._integral += error * dt
        
        # Clamp integral term
        max_integral = 50.0 / (self.ki + 0.001)
        self._integral = max(-max_integral, min(max_integral, self._integral))
        
        i_term = self.ki * self._integral
        
        self._prev_error = error
        
        # Total output
        output = p_term + i_term + d_term
        
        return output

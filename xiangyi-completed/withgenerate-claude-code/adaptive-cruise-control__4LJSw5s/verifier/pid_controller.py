"""
PID Controller Implementation for ACC System

Implements standard PID control with anti-windup and output saturation.
"""

class PIDController:
    """
    Proportional-Integral-Derivative controller for feedback control.
    
    Computes control output based on error: u(t) = Kp*e + Ki*∫e dt + Kd*de/dt
    """
    
    def __init__(self, kp, ki, kd, output_limits=None):
        """
        Initialize PID controller.
        
        Args:
            kp: Proportional gain (0-10 for ACC speed control)
            ki: Integral gain (0-5 for ACC systems)
            kd: Derivative gain (0-5 for ACC systems)
            output_limits: Tuple (min, max) for output saturation, optional
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self.reset()
    
    def reset(self):
        """Reset controller state for new control cycle."""
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, error, dt):
        """
        Compute control output given current error and time step.
        
        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds
            
        Returns:
            float: Control output value
        """
        # Proportional term: responds to current error
        p_term = self.kp * error
        
        # Integral term: accumulates error over time
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term: responds to rate of change of error
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0
        self.prev_error = error
        
        # Combine all terms
        output = p_term + i_term + d_term
        
        # Apply output saturation limits
        if self.output_limits:
            min_out, max_out = self.output_limits
            output = max(min_out, min(max_out, output))
            
            # Anti-windup: limit integral growth when saturated
            if output == min_out or output == max_out:
                # Don't accumulate more integral when saturated
                self.integral -= error * dt
        
        return output

import yaml

class PIDController:
    """PID controller for adaptive cruise control."""
    
    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        """Initialize PID controller.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output value (optional)
            output_max: Maximum output value (optional)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0
    
    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, error, dt):
        """Compute control output.
        
        Args:
            error: Control error (setpoint - measured_value)
            dt: Time step in seconds
            
        Returns:
            Control output value
        """
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        self.prev_error = error
        
        # Total output
        output = p_term + i_term + d_term
        
        # Output clamping (optional)
        if self.output_min is not None:
            output = max(output, self.output_min)
        if self.output_max is not None:
            output = min(output, self.output_max)
        
        return output

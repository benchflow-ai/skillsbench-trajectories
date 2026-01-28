class PIDController:
    """PID Controller for ACC system."""
    
    def __init__(self, kp, ki, kd):
        """Initialize PID controller with gains.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.reset()
    
    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, error, dt):
        """Compute control output.
        
        Args:
            error: Current error value
            dt: Time step
            
        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        
        # Update previous error
        self.prev_error = error
        
        # Return total control output
        return p_term + i_term + d_term

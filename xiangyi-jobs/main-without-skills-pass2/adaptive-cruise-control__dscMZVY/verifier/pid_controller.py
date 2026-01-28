class PIDController:
    """PID controller for speed and distance control."""
    
    def __init__(self, kp, ki, kd):
        """Initialize PID controller.
        
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
        """Compute PID output.
        
        Args:
            error: Current error signal
            dt: Time step in seconds
            
        Returns:
            float: PID output command
        """
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative
        
        # Store error for next iteration
        self.prev_error = error
        
        # Return total output
        return p_term + i_term + d_term

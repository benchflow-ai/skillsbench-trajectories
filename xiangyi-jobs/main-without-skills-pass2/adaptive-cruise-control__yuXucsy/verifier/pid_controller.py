class PIDController:
    """PID Controller for continuous control systems."""
    
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
        """Reset the controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, error, dt):
        """Compute control output based on error.
        
        Args:
            error: Current error value
            dt: Time step in seconds
            
        Returns:
            float: Control output
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
        
        # Update previous error
        self.prev_error = error
        
        # Return total control output
        return p_term + i_term + d_term

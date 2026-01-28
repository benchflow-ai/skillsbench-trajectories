class PIDController:
    """PID Controller for speed and distance control."""
    
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
        self.integral_error = 0.0
        self.prev_error = 0.0
    
    def reset(self):
        """Reset the controller state."""
        self.integral_error = 0.0
        self.prev_error = 0.0
    
    def compute(self, error, dt):
        """Compute PID output.
        
        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds
        
        Returns:
            float: PID controller output
        """
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral_error += error * dt
        i_term = self.ki * self.integral_error
        
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

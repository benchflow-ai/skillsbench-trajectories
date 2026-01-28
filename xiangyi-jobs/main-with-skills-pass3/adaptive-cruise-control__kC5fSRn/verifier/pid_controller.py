class PIDController:
    """PID Controller for feedback control systems."""
    
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
        self.integral = 0.0
        self.prev_error = 0.0
    
    def reset(self):
        """Clear controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
    
    def compute(self, error, dt):
        """Compute control output given error and timestep.
        
        Args:
            error: Current error value (setpoint - measured_value)
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
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        self.prev_error = error
        
        # Total output
        output = p_term + i_term + d_term
        
        return output

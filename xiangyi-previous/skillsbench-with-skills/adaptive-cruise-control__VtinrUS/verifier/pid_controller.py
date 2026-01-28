"""PID Controller implementation for ACC system with anti-windup."""

class PIDController:
    """A PID controller with anti-windup and derivative filtering."""
    
    def __init__(self, kp, ki, kd, output_limits=None):
        """
        Initialize PID controller with gains.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_limits: Tuple (min, max) for output clamping and anti-windup
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self.reset()
    
    def reset(self):
        """Reset the controller state."""
        self.integral = 0.0
        self.prev_error = None
        self.prev_derivative = 0.0
        self.prev_output = 0.0
    
    def compute(self, error, dt):
        """
        Compute PID control output with anti-windup.
        
        Args:
            error: Current error (setpoint - measured)
            dt: Time step in seconds
        
        Returns:
            float: Control output
        """
        if dt <= 0:
            return 0.0
        
        # Proportional term
        p_term = self.kp * error
        
        # Derivative term with filtering (compute before integral for anti-windup decision)
        if self.prev_error is None:
            derivative = 0.0
        else:
            derivative = (error - self.prev_error) / dt
        
        # Low-pass filter on derivative (alpha = 0.1 for more smoothing)
        alpha = 0.1
        filtered_derivative = alpha * derivative + (1 - alpha) * self.prev_derivative
        self.prev_derivative = filtered_derivative
        d_term = self.kd * filtered_derivative
        
        # Calculate output without integral to check for saturation
        pd_output = p_term + d_term
        
        # Anti-windup: only integrate if not saturated or if integral would reduce
        if self.output_limits is not None:
            min_out, max_out = self.output_limits
            
            # Check if we would be saturated
            test_output = pd_output + self.ki * self.integral
            
            # Conditional integration with back-calculation
            if test_output > max_out and error > 0:
                # Would saturate high and error is positive - don't increase integral
                pass
            elif test_output < min_out and error < 0:
                # Would saturate low and error is negative - don't decrease integral
                pass
            else:
                # Safe to integrate
                self.integral += error * dt
        else:
            self.integral += error * dt
        
        # Clamp integral to reasonable bounds
        max_integral = 100.0
        self.integral = max(-max_integral, min(max_integral, self.integral))
        
        i_term = self.ki * self.integral
        
        # Total output
        output = p_term + i_term + d_term
        
        # Clamp output if limits specified
        if self.output_limits is not None:
            min_out, max_out = self.output_limits
            output = max(min_out, min(max_out, output))
        
        self.prev_error = error
        self.prev_output = output
        
        return output

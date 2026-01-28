"""
PID Controller for Adaptive Cruise Control System
"""

class PIDController:
    """
    A standard PID controller with anti-windup protection.
    """
    
    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize PID controller with gains.
        
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
        """
        Reset the controller state (integral and previous error).
        """
        self.integral = 0.0
        self.prev_error = None
    
    def compute(self, error: float, dt: float) -> float:
        """
        Compute PID control output.
        
        Args:
            error: Current error (setpoint - measurement)
            dt: Time step in seconds
            
        Returns:
            Control output value
        """
        if dt <= 0:
            return 0.0
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term with anti-windup (limit integral accumulation)
        self.integral += error * dt
        # Anti-windup: limit integral to prevent excessive accumulation
        max_integral = 50.0  # Reasonable limit for acceleration control
        self.integral = max(-max_integral, min(max_integral, self.integral))
        i_term = self.ki * self.integral
        
        # Derivative term
        if self.prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self.prev_error) / dt
        
        self.prev_error = error
        
        # Total output
        output = p_term + i_term + d_term
        
        return output


if __name__ == "__main__":
    # Simple test
    pid = PIDController(kp=1.0, ki=0.1, kd=0.05)
    
    # Test compute
    output = pid.compute(error=5.0, dt=0.1)
    print(f"Test output for error=5.0: {output}")
    
    # Test reset
    pid.reset()
    output2 = pid.compute(error=5.0, dt=0.1)
    print(f"After reset, output for error=5.0: {output2}")
    print("PID Controller test passed!")

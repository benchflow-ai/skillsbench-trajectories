"""
PID Controller Implementation for Adaptive Cruise Control
"""

class PIDController:
    """
    A PID (Proportional-Integral-Derivative) controller for feedback control.
    
    The control law is:
        output = Kp * error + Ki * integral(error) + Kd * derivative(error)
    """
    
    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        """
        Initialize PID controller with gains and optional output limits.
        
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
        
        # Controller state
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True
    
    def reset(self):
        """
        Reset the controller state (integral and previous error).
        Call this when switching modes or reinitializing.
        """
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True
    
    def compute(self, error, dt):
        """
        Compute the control output given the current error and timestep.
        
        Args:
            error: Current error (setpoint - measured_value)
            dt: Time step in seconds
            
        Returns:
            float: Control output
        """
        if dt <= 0:
            return 0.0
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term (avoid derivative kick on first run)
        if self.first_run:
            derivative = 0.0
            self.first_run = False
        else:
            derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        self.prev_error = error
        
        # Total output
        output = p_term + i_term + d_term
        
        # Output clamping with anti-windup
        if self.output_min is not None and output < self.output_min:
            output = self.output_min
            # Anti-windup: prevent integral from growing when saturated
            if error * self.ki > 0:
                self.integral -= error * dt
        elif self.output_max is not None and output > self.output_max:
            output = self.output_max
            # Anti-windup: prevent integral from growing when saturated
            if error * self.ki < 0:
                self.integral -= error * dt
        
        return output


if __name__ == "__main__":
    # Simple test
    pid = PIDController(kp=1.0, ki=0.1, kd=0.05)
    
    setpoint = 30.0
    measured = 0.0
    dt = 0.1
    
    for i in range(50):
        error = setpoint - measured
        output = pid.compute(error, dt)
        measured += output * dt
        print(f"t={i*dt:.1f}s, error={error:.2f}, output={output:.2f}, measured={measured:.2f}")

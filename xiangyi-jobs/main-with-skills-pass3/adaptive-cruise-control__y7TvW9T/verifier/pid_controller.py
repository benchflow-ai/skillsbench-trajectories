class PIDController:
    def __init__(self, kp, ki, kd, min_out=None, max_out=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_out = min_out
        self.max_out = max_out
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
        
        # Proportional
        p_term = self.kp * error
        
        # Derivative
        derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        
        # Integral (Conditional Integration Anti-Windup)
        # Calculate what the output would be if we integrated
        temp_integral = self.integral + error * dt
        i_term = self.ki * temp_integral
        
        output = p_term + i_term + d_term
        
        # Check saturation and clamp
        saturated = False
        if self.max_out is not None and output > self.max_out:
            output = self.max_out
            saturated = True
            # If saturated high, only integrate if error is negative (reducing output)
            if error < 0:
                self.integral = temp_integral
        elif self.min_out is not None and output < self.min_out:
            output = self.min_out
            saturated = True
            # If saturated low, only integrate if error is positive (increasing output)
            if error > 0:
                self.integral = temp_integral
        else:
            # Not saturated, update integral normally
            self.integral = temp_integral
            
        self.prev_error = error
        return output

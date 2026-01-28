class PIDController:
    def __init__(self, kp, ki, kd, output_limits=(None, None)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self.integral = 0
        self.prev_error = 0

    def reset(self):
        self.integral = 0
        self.prev_error = 0

    def compute(self, error, dt):
        if dt <= 0:
            return 0
        
        # Proportional term
        p = self.kp * error
        
        # Integral term
        self.integral += error * dt
        i = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.prev_error) / dt
        d = self.kd * derivative
        self.prev_error = error
        
        output = p + i + d
        
        # Anti-windup
        lower, upper = self.output_limits
        if lower is not None or upper is not None:
            if upper is not None and output > upper:
                # If output is saturated, we stop integrating if the error has the same sign
                if error > 0:
                    self.integral -= error * dt
                output = upper
            elif lower is not None and output < lower:
                if error < 0:
                    self.integral -= error * dt
                output = lower
                
        return output

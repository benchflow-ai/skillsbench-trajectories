class PIDController:
    def __init__(self, kp, ki, kd, output_limits=(None, None)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.previous_error = 0.0

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
            
        self.integral += error * dt
        
        # Simple windup protection: clamp integral such that ki * integral is within limits
        if self.ki != 0:
            if self.output_limits[1] is not None:
                self.integral = min(self.integral, self.output_limits[1] / self.ki)
            if self.output_limits[0] is not None:
                self.integral = max(self.integral, self.output_limits[0] / self.ki)
                
        derivative = (error - self.previous_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        
        self.previous_error = error
        
        # Clamp output
        if self.output_limits[0] is not None:
            output = max(self.output_limits[0], output)
        if self.output_limits[1] is not None:
            output = min(self.output_limits[1], output)
            
        return output
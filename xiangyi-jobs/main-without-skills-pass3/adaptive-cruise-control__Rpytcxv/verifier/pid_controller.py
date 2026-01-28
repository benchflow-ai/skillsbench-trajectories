
class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True

    def compute(self, error, dt):
        if dt <= 0.0:
            return 0.0
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term
        if self.first_run:
            d_term = 0.0
            self.first_run = False
        else:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative
            
        self.prev_error = error
        
        return p_term + i_term + d_term

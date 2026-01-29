class PIDController:
    def __init__(self, kp, ki, kd, output_limits=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits # tuple (min, max) or None
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True

    def compute(self, error, dt):
        # Handle first run to avoid derivative kick
        if self.first_run:
            self.prev_error = error
            self.first_run = False
            derivative = 0.0
        else:
            derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        
        p_term = self.kp * error
        d_term = self.kd * derivative
        
        # Tentative integral update
        self.integral += error * dt
        
        # Calculate total
        output = p_term + (self.ki * self.integral) + d_term
        
        if self.output_limits:
            min_out, max_out = self.output_limits
            
            final_output = output
            if output > max_out:
                final_output = max_out
                # Conditional Integration: Undo integration if saturated and error is driving it further
                # If error > 0, we are adding to integral, making it worse.
                if error > 0:
                    self.integral -= error * dt
            elif output < min_out:
                final_output = min_out
                if error < 0:
                    self.integral -= error * dt
            
            self.prev_error = error
            return final_output
        else:
            self.prev_error = error
            return output

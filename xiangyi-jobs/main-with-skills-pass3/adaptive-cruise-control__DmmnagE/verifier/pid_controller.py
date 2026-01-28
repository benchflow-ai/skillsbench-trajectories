class PIDController:
    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral += error * dt
        
        # Simple anti-windup: limit integral contribution
        # We'll use a more sophisticated approach if needed, but let's start with this
        i_term = self.ki * self.integral

        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        self.prev_error = error

        output = p_term + i_term + d_term

        # If output is saturated, stop integrating
        if self.output_min is not None and output < self.output_min:
            if error < 0: # Still making it worse
                self.integral -= error * dt
            output = self.output_min
        elif self.output_max is not None and output > self.output_max:
            if error > 0: # Still making it worse
                self.integral -= error * dt
            output = self.output_max

        return output

class PIDController:
    def __init__(self, kp, ki, kd, i_limit=10.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.i_limit = i_limit
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Clear controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """Compute control output given error and timestep."""
        if dt <= 0:
            return 0.0
            
        # Proportional term
        p_term = self.kp * error

        # Integral term with clamping
        self.integral += error * dt
        self.integral = max(-self.i_limit, min(self.integral, self.i_limit))
        i_term = self.ki * self.integral

        # Derivative term
        derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        self.prev_error = error

        # Total output
        return p_term + i_term + d_term
"""PID controller implementation for ACC simulation."""


class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        """Reset integral and derivative state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        """Compute PID output given error and timestep."""
        if dt <= 0:
            return 0.0

        p_term = self.kp * error
        self.integral += error * dt
        i_term = self.ki * self.integral

        if not self.initialized:
            derivative = 0.0
            self.initialized = True
        else:
            derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        self.prev_error = error

        return p_term + i_term + d_term

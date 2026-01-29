class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0

        # Proportional
        p_term = self.kp * error

        # Integral
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative
        if not self.initialized:
            derivative = 0.0
            self.initialized = True
        else:
            derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative

        self.prev_error = error

        return p_term + i_term + d_term

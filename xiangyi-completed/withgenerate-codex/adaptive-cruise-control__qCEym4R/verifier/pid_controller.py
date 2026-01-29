class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False
        self.integral_limit = 50.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        if dt <= 0.0:
            return 0.0
        if self.initialized and (error * self.prev_error < 0.0):
            self.integral = 0.0
        self.integral += error * dt
        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
        if self.integral < -self.integral_limit:
            self.integral = -self.integral_limit
        if not self.initialized:
            derivative = 0.0
            self.initialized = True
        else:
            derivative = (error - self.prev_error) / dt
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

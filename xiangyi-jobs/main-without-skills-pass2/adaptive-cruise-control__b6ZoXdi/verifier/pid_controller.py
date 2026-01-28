class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.first = True
        # simple anti-windup clamp
        self.integral_limit = 100.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.first = True

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
        # integral term with clamp
        self.integral += error * dt
        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
        elif self.integral < -self.integral_limit:
            self.integral = -self.integral_limit

        if self.first:
            derivative = 0.0
            self.first = False
        else:
            derivative = (error - self.prev_error) / dt
        self.prev_error = error

        return self.kp * error + self.ki * self.integral + self.kd * derivative

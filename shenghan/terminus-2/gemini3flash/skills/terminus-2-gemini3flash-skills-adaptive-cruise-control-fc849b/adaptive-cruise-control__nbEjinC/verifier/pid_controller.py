class PIDController:
    def __init__(self, kp, ki, kd, i_limit=10.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.i_limit = i_limit

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt, saturated=False):
        if dt <= 0:
            return 0.0
        if not saturated:
            self.integral += error * dt
            self.integral = max(-self.i_limit, min(self.integral, self.i_limit))
        derivative = (error - self.prev_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

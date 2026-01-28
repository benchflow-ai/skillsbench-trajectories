class PIDController:
    def __init__(self, kp, ki, kd, integrator_limit=10.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integrator_limit = integrator_limit
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
        # Integral term with simple anti-windup
        self.integral += error * dt
        if self.integrator_limit is not None:
            self.integral = max(-self.integrator_limit, min(self.integrator_limit, self.integral))
        # Derivative term
        if self.prev_error is None:
            derivative = 0.0
        else:
            derivative = (error - self.prev_error) / dt
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative

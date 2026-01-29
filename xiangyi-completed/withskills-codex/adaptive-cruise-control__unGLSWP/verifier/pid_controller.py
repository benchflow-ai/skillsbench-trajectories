class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.integral = 0.0
        self.prev_error = 0.0
        self._has_prev = False

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self._has_prev = False

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0

        p_term = self.kp * error
        if self._has_prev and error * self.prev_error < 0:
            self.integral = 0.0
        self.integral += error * dt
        i_term = self.ki * self.integral

        if self._has_prev:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        self.prev_error = error
        self._has_prev = True

        return p_term + i_term + d_term

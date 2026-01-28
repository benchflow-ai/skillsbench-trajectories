class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.reset()

    def reset(self):
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
        self._integral += error * dt
        if self._prev_error is None:
            derivative = 0.0
        else:
            derivative = (error - self._prev_error) / dt
        self._prev_error = error
        return (self.kp * error) + (self.ki * self._integral) + (self.kd * derivative)

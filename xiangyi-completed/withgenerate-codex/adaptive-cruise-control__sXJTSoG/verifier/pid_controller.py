class PIDController:
    """Simple discrete-time PID controller."""

    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.reset()

    def reset(self):
        self._prev_error = 0.0
        self._integral = 0.0

    def compute(self, error, dt):
        if dt <= 0.0:
            return 0.0

        # Trapezoidal integration for smoother integral term.
        self._integral += 0.5 * (error + self._prev_error) * dt
        derivative = (error - self._prev_error) / dt
        self._prev_error = error

        return self.kp * error + self.ki * self._integral + self.kd * derivative

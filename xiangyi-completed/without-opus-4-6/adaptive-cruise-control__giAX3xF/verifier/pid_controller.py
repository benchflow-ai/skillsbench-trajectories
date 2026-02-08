class PIDController:
    """PID controller with anti-windup protection."""

    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.reset()

    def reset(self):
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error, dt):
        """Compute PID output given current error and timestep.

        Args:
            error: Current error (setpoint - measured).
            dt: Time step in seconds.

        Returns:
            float: Control output.
        """
        # Proportional term
        p = self.kp * error

        # Integral term with anti-windup clamp
        self._integral += error * dt
        # Clamp integral to prevent excessive windup
        max_integral = 50.0 / (self.ki if self.ki > 0 else 1.0)
        self._integral = max(-max_integral, min(max_integral, self._integral))
        i = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d = 0.0
        else:
            d = self.kd * (error - self._prev_error) / dt
        self._prev_error = error

        return p + i + d

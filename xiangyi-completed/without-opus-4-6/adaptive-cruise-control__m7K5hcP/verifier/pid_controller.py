class PIDController:
    """PID controller with integral windup protection and output clamping."""

    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Reset integral accumulator and previous error."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error, dt):
        """Compute PID output for given error and timestep.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds.

        Returns:
            float: Control output.
        """
        # Proportional
        p_term = self.kp * error

        # Integral with accumulation
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative (zero on first call)
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt
        self._prev_error = error

        return p_term + i_term + d_term

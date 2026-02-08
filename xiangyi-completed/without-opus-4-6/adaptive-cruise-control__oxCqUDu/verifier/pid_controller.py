class PIDController:
    """PID controller with anti-windup and derivative filtering."""

    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = None

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error, dt):
        """Compute PID output.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds.

        Returns:
            float: Control output.
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup clamp
        self.integral += error * dt
        self.integral = max(-50.0, min(50.0, self.integral))
        i_term = self.ki * self.integral

        # Derivative term
        if self.prev_error is not None:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0
        self.prev_error = error

        return p_term + i_term + d_term

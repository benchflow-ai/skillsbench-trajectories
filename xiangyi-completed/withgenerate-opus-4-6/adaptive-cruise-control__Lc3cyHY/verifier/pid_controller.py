"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID controller with anti-windup protection."""

    def __init__(self, kp, ki, kd, integral_limit=None):
        """Initialize PID controller with gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            integral_limit: Max absolute value for integral term (anti-windup)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def compute(self, error, dt):
        """Compute PID control output.

        Args:
            error: Current error (setpoint - measured)
            dt: Time step in seconds

        Returns:
            float: Control output
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term with accumulation and anti-windup
        self.integral += error * dt
        if self.integral_limit is not None:
            self.integral = max(-self.integral_limit,
                                min(self.integral_limit, self.integral))
        i_term = self.ki * self.integral

        # Derivative term (skip on first call to avoid spike)
        if self.first_call:
            d_term = 0.0
            self.first_call = False
        else:
            d_term = self.kd * (error - self.prev_error) / dt

        self.prev_error = error

        output = p_term + i_term + d_term
        return output

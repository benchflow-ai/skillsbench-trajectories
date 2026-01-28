"""PID Controller for Adaptive Cruise Control."""


class PIDController:
    """A proportional-integral-derivative controller for feedback control."""

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - actual)
            dt: Time step in seconds

        Returns:
            Control output (float)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup (limit accumulation)
        self.integral += error * dt
        self.integral = max(-100, min(100, self.integral))  # Clamp integral
        i_term = self.ki * self.integral

        # Derivative term (approximate from error change)
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        self.prev_error = error

        return p_term + i_term + d_term

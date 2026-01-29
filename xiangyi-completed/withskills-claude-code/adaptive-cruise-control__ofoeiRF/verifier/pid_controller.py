"""PID Controller implementation for ACC system."""


class PIDController:
    """Proportional-Integral-Derivative controller."""

    def __init__(self, kp, ki, kd, integral_limit=100.0):
        """
        Initialize PID controller with gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            integral_limit: Maximum absolute value for integral term
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.reset()

    def reset(self):
        """Reset the PID controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute control output based on error.

        Args:
            error: Current error value
            dt: Time step (seconds)

        Returns:
            float: Control output
        """
        # Update integral with anti-windup
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))

        # Compute derivative
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0

        # PID output
        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        self.prev_error = error

        return output

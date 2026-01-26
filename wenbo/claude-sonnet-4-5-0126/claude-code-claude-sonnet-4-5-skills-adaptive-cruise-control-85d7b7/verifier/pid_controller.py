"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """PID Controller for closed-loop control."""

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.reset()

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """Compute control output based on error.

        Args:
            error: Current error value
            dt: Time step

        Returns:
            Control output (float)
        """
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return output

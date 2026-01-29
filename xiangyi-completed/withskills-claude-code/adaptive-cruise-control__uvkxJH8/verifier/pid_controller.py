"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A standard PID controller with anti-windup protection."""

    def __init__(self, kp: float, ki: float, kd: float,
                 integral_limit: float = 50.0):
        """Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            integral_limit: Maximum absolute value for integral term (anti-windup)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.reset()

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """Compute the control output based on the error.

        Args:
            error: The current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            The control output value
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term with accumulation and anti-windup clamping
        self._integral += error * dt
        # Clamp integral to prevent windup
        self._integral = max(-self.integral_limit, min(self.integral_limit, self._integral))
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt

        self._prev_error = error

        return p_term + i_term + d_term

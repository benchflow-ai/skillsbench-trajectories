"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID (Proportional-Integral-Derivative) controller.

    Computes control output based on error between setpoint and measured value.
    """

    def __init__(self, kp: float, ki: float, kd: float,
                 integral_limit: float = 10.0):
        """Initialize the PID controller with gains.

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
        """Compute PID control output.

        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            Control output value
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup (clamping)
        self._integral += error * dt
        self._integral = max(-self.integral_limit, min(self.integral_limit, self._integral))
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
            d_term = self.kd * derivative

        self._prev_error = error

        return p_term + i_term + d_term

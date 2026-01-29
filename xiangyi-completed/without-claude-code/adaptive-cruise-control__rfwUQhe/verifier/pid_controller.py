"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID (Proportional-Integral-Derivative) controller.

    Attributes:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """Initialize the PID controller with given gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._integral = 0.0
        self._prev_error = None

    def reset(self) -> None:
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float, integral_limit: float = 50.0) -> float:
        """Compute the PID control output.

        Args:
            error: The current error (setpoint - measured value)
            dt: Time step in seconds
            integral_limit: Maximum absolute value for integral term (anti-windup)

        Returns:
            The control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self._integral += error * dt
        # Clamp integral to prevent windup
        self._integral = max(-integral_limit, min(integral_limit, self._integral))
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt

        self._prev_error = error

        return p_term + i_term + d_term

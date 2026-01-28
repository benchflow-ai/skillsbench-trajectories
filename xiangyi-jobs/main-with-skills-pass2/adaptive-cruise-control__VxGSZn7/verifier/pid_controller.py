"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID (Proportional-Integral-Derivative) controller."""

    def __init__(self, kp: float, ki: float, kd: float):
        """Initialize the PID controller with gains.

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
            The control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with accumulation
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
            d_term = self.kd * derivative

        self._prev_error = error

        return p_term + i_term + d_term

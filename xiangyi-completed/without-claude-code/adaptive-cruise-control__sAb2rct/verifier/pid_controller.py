"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """
    A PID (Proportional-Integral-Derivative) controller.

    Attributes:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize the PID controller.

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
        """
        Compute the control output based on the error.

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

        # Integral term with anti-windup
        # Only integrate when error is small to prevent windup during saturation
        if abs(error) < 10.0:
            self._integral += error * dt
        # Limit integral to prevent windup
        max_integral = 20.0
        self._integral = max(-max_integral, min(max_integral, self._integral))
        i_term = self.ki * self._integral

        # Derivative term with filtering
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt

        self._prev_error = error

        return p_term + i_term + d_term

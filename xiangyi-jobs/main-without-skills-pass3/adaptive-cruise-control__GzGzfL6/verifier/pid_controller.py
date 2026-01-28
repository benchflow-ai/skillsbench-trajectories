"""
PID Controller for Adaptive Cruise Control System
"""


class PIDController:
    """
    A PID (Proportional-Integral-Derivative) controller implementation.

    The controller computes control output based on the error between
    desired and actual values using the formula:
    output = Kp * error + Ki * integral(error) + Kd * derivative(error)
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize the PID controller with gain parameters.

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
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float, output_limits: tuple = None) -> float:
        """
        Compute the control output based on the current error.

        Args:
            error: The current error (setpoint - measured value)
            dt: Time step in seconds
            output_limits: Optional tuple (min, max) for anti-windup

        Returns:
            The control output value
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup (clamping)
        self._integral += error * dt

        # Apply integral clamping for anti-windup
        if output_limits is not None:
            min_out, max_out = output_limits
            max_integral = max_out / self.ki if self.ki > 0 else float('inf')
            min_integral = min_out / self.ki if self.ki > 0 else float('-inf')
            self._integral = max(min_integral, min(max_integral, self._integral))

        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            derivative = (error - self._prev_error) / dt
            d_term = self.kd * derivative

        self._prev_error = error

        return p_term + i_term + d_term

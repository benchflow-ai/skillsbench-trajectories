"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A standard PID controller with anti-windup protection."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = None, output_max: float = None):
        """
        Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output value for anti-windup (optional)
            output_max: Maximum output value for anti-windup (optional)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """
        Compute the PID control output.

        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            Control output value
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term with accumulation
        self._integral += error * dt

        # Anti-windup: clamp integral if output limits are specified
        if self.output_min is not None and self.output_max is not None and self.ki > 0:
            max_integral = self.output_max / self.ki
            min_integral = self.output_min / self.ki
            self._integral = max(min_integral, min(max_integral, self._integral))

        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt

        self._prev_error = error

        output = p_term + i_term + d_term

        # Clamp output if limits specified
        if self.output_min is not None:
            output = max(self.output_min, output)
        if self.output_max is not None:
            output = min(self.output_max, output)

        return output

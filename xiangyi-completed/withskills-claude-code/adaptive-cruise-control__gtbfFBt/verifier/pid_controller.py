"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID (Proportional-Integral-Derivative) controller with anti-windup.

    Attributes:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
    """

    def __init__(self, kp: float, ki: float, kd: float, output_limits: tuple = None):
        """Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_limits: Optional tuple (min, max) for output clamping
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self._integral = 0.0
        self._prev_error = None

    def reset(self) -> None:
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

        # Derivative term (compute before integral to use in anti-windup decision)
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt if dt > 0 else 0.0

        # Compute what output would be without new integral
        output_without_new_integral = p_term + self.ki * self._integral + d_term

        # Conditional integration: only integrate if output is not saturated
        # or if integration would reduce the saturation
        should_integrate = True
        if self.output_limits is not None:
            min_out, max_out = self.output_limits
            if output_without_new_integral >= max_out and error > 0:
                should_integrate = False  # Saturated high, positive error would increase
            elif output_without_new_integral <= min_out and error < 0:
                should_integrate = False  # Saturated low, negative error would decrease

        if should_integrate:
            self._integral += error * dt

        # Anti-windup: clamp integral to reasonable bounds
        max_integral = 30.0  # Limit integral contribution
        self._integral = max(-max_integral, min(max_integral, self._integral))

        i_term = self.ki * self._integral

        self._prev_error = error

        output = p_term + i_term + d_term

        # Apply output limits if specified
        if self.output_limits is not None:
            min_out, max_out = self.output_limits
            output = max(min_out, min(max_out, output))

        return output

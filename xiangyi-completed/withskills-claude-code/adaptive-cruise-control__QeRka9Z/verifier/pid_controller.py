"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A standard PID controller with anti-windup and output limiting."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = -8.0, output_max: float = 3.0):
        """Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output value (for anti-windup)
            output_max: Maximum output value (for anti-windup)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.reset()

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """Compute PID control output.

        Args:
            error: Current error (setpoint - measured)
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
        i_term = self.ki * self._integral

        # Derivative term (on error)
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt

        self._prev_error = error

        # Total output before clamping
        output = p_term + i_term + d_term

        # Anti-windup: prevent integral from growing when output is saturated
        if output > self.output_max:
            # Undo the integral accumulation that pushed us over the limit
            if error > 0:  # Only if error would make it worse
                self._integral -= error * dt
            output = self.output_max
        elif output < self.output_min:
            # Undo the integral accumulation that pushed us under the limit
            if error < 0:  # Only if error would make it worse
                self._integral -= error * dt
            output = self.output_min

        return output

"""PID Controller for Adaptive Cruise Control."""


class PIDController:
    """A PID controller with anti-windup and output clamping."""

    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        """Initialize the PID controller.

        Args:
            kp: Proportional gain.
            ki: Integral gain.
            kd: Derivative gain.
            output_min: Minimum output value (optional).
            output_max: Maximum output value (optional).
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max

        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Reset the controller state."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error, dt):
        """Compute the PID control output.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds.

        Returns:
            Control output as a float.
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is not None:
            d_term = self.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0
        self._prev_error = error

        output = p_term + i_term + d_term

        # Clamp output and apply anti-windup
        if self.output_min is not None and output < self.output_min:
            output = self.output_min
            # Anti-windup: prevent integral from growing when saturated
            self._integral -= error * dt
        elif self.output_max is not None and output > self.output_max:
            output = self.output_max
            self._integral -= error * dt

        return output

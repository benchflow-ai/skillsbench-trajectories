"""PID Controller for Adaptive Cruise Control."""


class PIDController:
    """A standard PID controller with integral windup protection."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = None, output_max: float = None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Reset controller state."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """Compute PID output given current error and timestep.

        Args:
            error: Current error (setpoint - measured).
            dt: Time step in seconds.

        Returns:
            Control output (float).
        """
        # Proportional
        p_term = self.kp * error

        # Integral with anti-windup (only accumulate if not saturated)
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative (on error)
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt
        self._prev_error = error

        output = p_term + i_term + d_term

        # Clamp output and apply anti-windup
        if self.output_min is not None and output < self.output_min:
            # Back-calculate integral to prevent windup
            self._integral -= error * dt
            output = self.output_min
        elif self.output_max is not None and output > self.output_max:
            self._integral -= error * dt
            output = self.output_max

        return output

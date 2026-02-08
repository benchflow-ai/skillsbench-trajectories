"""PID Controller for Adaptive Cruise Control."""


class PIDController:
    """A PID controller with integral windup protection."""

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with gains.

        Args:
            kp: Proportional gain.
            ki: Integral gain.
            kd: Derivative gain.
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._integral = 0.0
        self._prev_error = None
        self.integral_limit = 50.0

    def reset(self):
        """Reset the controller state."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error, dt):
        """Compute PID output given the current error and timestep.

        Args:
            error: Current error (setpoint - measured).
            dt: Time step in seconds.

        Returns:
            Control output as a float.
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup clamping
        self._integral += error * dt
        self._integral = max(-self.integral_limit, min(self.integral_limit, self._integral))
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is not None:
            d_term = self.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0
        self._prev_error = error

        return p_term + i_term + d_term

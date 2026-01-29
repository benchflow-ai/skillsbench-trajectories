"""PID Controller for Adaptive Cruise Control system."""


class PIDController:
    """A standard PID controller for ACC speed and distance control."""

    def __init__(self, kp, ki, kd):
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
        self.integral_error = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Reset the controller state."""
        self.integral_error = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute the control output based on the error.

        Args:
            error: Current error (setpoint - actual)
            dt: Time step in seconds

        Returns:
            Control output (float)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral_error += error * dt
        i_term = self.ki * self.integral_error

        # Derivative term
        d_term = 0.0
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt

        self.prev_error = error

        return p_term + i_term + d_term

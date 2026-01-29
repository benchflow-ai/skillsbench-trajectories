"""PID Controller implementation for ACC system."""


class PIDController:
    """A standard PID controller for ACC speed and distance control."""

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller.

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
        """Reset the controller state."""
        self.integral_error = 0.0
        self.previous_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error value
            dt: Time step in seconds

        Returns:
            Control output (acceleration command in m/s^2)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral_error += error * dt
        i_term = self.ki * self.integral_error

        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self.previous_error) / dt
        else:
            d_term = 0.0

        self.previous_error = error

        return p_term + i_term + d_term

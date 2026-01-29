"""PID Controller for ACC system."""


class PIDController:
    """Proportional-Integral-Derivative controller."""

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

        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def compute(self, error, dt):
        """
        Compute control output.

        Args:
            error: Current error value
            dt: Time step

        Returns:
            Control output (float)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if self.first_call:
            d_term = 0.0
            self.first_call = False
        else:
            d_term = self.kd * (error - self.prev_error) / dt

        # Store error for next iteration
        self.prev_error = error

        # Compute output
        output = p_term + i_term + d_term

        return output

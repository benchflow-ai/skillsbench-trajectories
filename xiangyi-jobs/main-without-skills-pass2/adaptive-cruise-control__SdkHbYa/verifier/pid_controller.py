"""PID Controller implementation for ACC system."""


class PIDController:
    """A simple PID controller for managing errors."""

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
        self.integral_error = 0.0
        self.previous_error = 0.0

    def reset(self):
        """Reset the integral and previous error."""
        self.integral_error = 0.0
        self.previous_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID output.

        Args:
            error: Current error value
            dt: Time step in seconds

        Returns:
            float: PID controller output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral_error += error * dt
        # Limit integral to prevent windup
        self.integral_error = max(-10.0, min(10.0, self.integral_error))
        i_term = self.ki * self.integral_error

        # Derivative term
        if dt > 0:
            derivative_error = (error - self.previous_error) / dt
        else:
            derivative_error = 0.0
        d_term = self.kd * derivative_error

        # Update previous error
        self.previous_error = error

        return p_term + i_term + d_term

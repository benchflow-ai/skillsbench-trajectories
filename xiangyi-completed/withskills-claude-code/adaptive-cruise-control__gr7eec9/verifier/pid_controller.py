"""PID Controller for Adaptive Cruise Control system."""


class PIDController:
    """PID controller for feedback control."""

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
        """Reset internal state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID output.

        Args:
            error: Current error (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        self.prev_error = error

        # Return sum of all terms
        return p_term + i_term + d_term

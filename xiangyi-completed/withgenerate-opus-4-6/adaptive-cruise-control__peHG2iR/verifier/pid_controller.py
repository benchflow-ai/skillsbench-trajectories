"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A discrete PID controller with anti-windup and derivative filtering."""

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with gains.

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
        """Compute PID control output.

        Args:
            error: Current error (setpoint - measured)
            dt: Time step in seconds

        Returns:
            float: Control output
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

        self.prev_error = error

        return p_term + i_term + d_term

"""PID Controller for vehicle speed and distance control."""


class PIDController:
    """Simple PID controller for ACC system."""

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
        self.prev_error = 0.0

    def reset(self):
        """Reset controller state."""
        self.integral_error = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with clamping to prevent windup
        self.integral_error += error * dt
        # Clamp integral error to reasonable bounds
        self.integral_error = max(-10.0, min(10.0, self.integral_error))
        i_term = self.ki * self.integral_error

        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        self.prev_error = error

        # Total output
        output = p_term + i_term + d_term

        return output

"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID (Proportional-Integral-Derivative) controller.

    Computes control output based on error between setpoint and measured value.
    """

    def __init__(self, kp: float, ki: float, kd: float, integral_limit: float = 50.0):
        """Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            integral_limit: Maximum absolute value for integral term (anti-windup)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.reset()

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """Compute the control output based on current error.

        Args:
            error: The difference between setpoint and measured value
            dt: Time step in seconds

        Returns:
            The control output (acceleration command)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        # Clamp integral to prevent windup
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        i_term = self.ki * self.integral

        # Derivative term
        if self.prev_error is None:
            d_term = 0.0
        else:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative

        self.prev_error = error

        return p_term + i_term + d_term

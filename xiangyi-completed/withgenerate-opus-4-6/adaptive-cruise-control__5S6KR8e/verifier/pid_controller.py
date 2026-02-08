"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """Discrete PID controller with anti-windup and derivative filtering."""

    def __init__(self, kp: float, ki: float, kd: float,
                 integral_limit: float = 50.0, derivative_filter: float = 0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.alpha = derivative_filter  # Low-pass filter coefficient (0-1)
        self.integral = 0.0
        self.prev_error = None
        self.filtered_derivative = 0.0

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = None
        self.filtered_derivative = 0.0

    def compute(self, error: float, dt: float) -> float:
        """Compute PID output given current error and timestep.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds.

        Returns:
            Control output (float).
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup clamping
        self.integral += error * dt
        self.integral = max(-self.integral_limit,
                            min(self.integral_limit, self.integral))
        i_term = self.ki * self.integral

        # Derivative term with low-pass filter to handle noisy signals
        if self.prev_error is not None:
            raw_derivative = (error - self.prev_error) / dt
            self.filtered_derivative = (self.alpha * raw_derivative +
                                        (1.0 - self.alpha) * self.filtered_derivative)
        else:
            self.filtered_derivative = 0.0
        d_term = self.kd * self.filtered_derivative

        self.prev_error = error

        return p_term + i_term + d_term

"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A discrete PID controller with anti-windup clamping."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = None, output_max: float = None):
        """Initialize PID controller with gains.

        Args:
            kp: Proportional gain.
            ki: Integral gain.
            kd: Derivative gain.
            output_min: Minimum output for anti-windup (optional).
            output_max: Maximum output for anti-windup (optional).
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = None

    def reset(self):
        """Reset controller internal state."""
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """Compute PID control output.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds.

        Returns:
            Control output as a float.
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with accumulation
        self.integral += error * dt

        # Anti-windup: clamp integral so output stays in bounds
        if self.output_min is not None and self.output_max is not None:
            max_integral = self.output_max / max(self.ki, 1e-10)
            min_integral = self.output_min / max(self.ki, 1e-10)
            self.integral = max(min_integral, min(max_integral, self.integral))

        i_term = self.ki * self.integral

        # Derivative term
        if self.prev_error is not None:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        self.prev_error = error

        output = p_term + i_term + d_term

        # Clamp output
        if self.output_min is not None:
            output = max(self.output_min, output)
        if self.output_max is not None:
            output = min(self.output_max, output)

        return output

"""PID Controller implementation for Adaptive Cruise Control system."""

class PIDController:
    """Proportional-Integral-Derivative controller for speed and distance control."""

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.previous_error = 0.0
        self.integral = 0.0

    def reset(self):
        """Reset controller internal state (integral and derivative terms)."""
        self.previous_error = 0.0
        self.integral = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - measured_value)
            dt: Time step in seconds

        Returns:
            float: Control output (acceleration command)
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        proportional = self.kp * error

        # Integral term with anti-windup (limit integral accumulation)
        self.integral += error * dt
        # Anti-windup: limit integral term to reasonable bounds
        max_integral = 100.0
        self.integral = max(-max_integral, min(max_integral, self.integral))
        integral = self.ki * self.integral

        # Derivative term
        derivative = 0.0
        if dt > 0:
            derivative = self.kd * (error - self.previous_error) / dt

        # Store error for next iteration
        self.previous_error = error

        # Combined PID output
        output = proportional + integral + derivative

        return output

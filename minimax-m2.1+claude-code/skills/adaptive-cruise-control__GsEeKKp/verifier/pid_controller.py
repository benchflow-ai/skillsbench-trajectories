"""PID Controller implementation for Adaptive Cruise Control system."""

class PIDController:
    """Proportional-Integral-Derivative controller for speed and distance control."""

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

    def reset(self):
        """Reset controller internal state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID output.

        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            float: Control output
        """
        # Proportional term
        proportional = self.kp * error

        # Integral term with anti-windup
        # Only integrate if output is not saturated (assuming output limits of [-8, 3])
        output_unclamped = proportional
        if self.ki > 0:
            # Check if we're in a region where integral should be updated
            # Simple anti-windup: clamp integral when error is large and consistent sign
            self.integral += error * dt
            # Clamp integral to prevent windup (tuned for our acceleration range)
            max_integral = 3.0 / max(self.ki, 0.001)  # Max output / ki
            self.integral = max(-max_integral, min(max_integral, self.integral))
        integral = self.ki * self.integral

        # Derivative term
        derivative = 0.0
        if dt > 0:
            derivative = self.kd * (error - self.prev_error) / dt

        # Update previous error
        self.prev_error = error

        # Combine all terms
        output = proportional + integral + derivative

        return output

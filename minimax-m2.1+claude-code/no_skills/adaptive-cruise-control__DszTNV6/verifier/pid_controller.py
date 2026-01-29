"""
PID Controller for Adaptive Cruise Control system.
"""

class PIDController:
    """Proportional-Integral-Derivative controller."""

    def __init__(self, kp: float = 0.0, ki: float = 0.0, kd: float = 0.0):
        """
        Initialize PID controller with given gains.

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
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        """
        Compute PID output given error and timestep.

        Args:
            error: Current error signal
            dt: Time step in seconds

        Returns:
            Control output
        """
        # Proportional term
        proportional = self.kp * error

        # Integral term (with anti-windup check)
        self.integral += error * dt
        integral = self.ki * self.integral

        # Derivative term
        derivative = 0.0
        if dt > 0:
            derivative = self.kd * (error - self.prev_error) / dt

        # Store error for next iteration
        self.prev_error = error

        return proportional + integral + derivative

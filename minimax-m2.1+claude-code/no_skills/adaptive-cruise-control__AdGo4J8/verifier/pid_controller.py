"""PID Controller for Adaptive Cruise Control System."""

class PIDController:
    """Proportional-Integral-Derivative controller."""

    def __init__(self, kp: float = 0.0, ki: float = 0.0, kd: float = 0.0):
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
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        """
        Compute PID output.

        Args:
            error: Current error signal
            dt: Time step in seconds

        Returns:
            Control output
        """
        # Proportional term
        proportional = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        integral = self.ki * self.integral

        # Derivative term (on measurement to avoid derivative kick)
        derivative = 0.0
        if dt > 0:
            derivative = self.kd * (error - self.prev_error) / dt
        self.prev_error = error

        return proportional + integral + derivative

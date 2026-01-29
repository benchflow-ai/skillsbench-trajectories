"""PID Controller implementation for ACC system."""


class PIDController:
    """Proportional-Integral-Derivative controller.

    Attributes:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """Initialize PID controller with given gains.

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
        """Reset controller state (integral and derivative terms)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error: float, dt: float) -> float:
        """Compute PID output given error and time step.

        Args:
            error: Current error value (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            Control output (float)
        """
        # Proportional term
        proportional = self.kp * error

        # Integral term
        self.integral += error * dt
        integral = self.ki * self.integral

        # Derivative term (using simple difference if initialized)
        if self.initialized and dt > 0:
            derivative = self.kd * (error - self.prev_error) / dt
        else:
            derivative = 0.0

        self.prev_error = error
        self.initialized = True

        return proportional + integral + derivative

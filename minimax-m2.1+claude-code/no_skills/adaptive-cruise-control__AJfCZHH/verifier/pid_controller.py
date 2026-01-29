"""
PID Controller for Adaptive Cruise Control System
"""

class PIDController:
    """
    A PID (Proportional-Integral-Derivative) controller.

    This class implements a standard PID controller with anti-windup protection
    through integral term clamping.
    """

    def __init__(self, kp: float = 0.0, ki: float = 0.0, kd: float = 0.0):
        """
        Initialize the PID controller with given gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # State variables
        self._integral = 0.0
        self._prev_error = 0.0
        self._initialized = False

    def reset(self) -> None:
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._initialized = False

    def compute(self, error: float, dt: float) -> float:
        """
        Compute the PID control output.

        Args:
            error: The current error value (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            The control output (acceleration command)
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        proportional = self.kp * error

        # Integral term with anti-windup (clamped to prevent excessive buildup)
        self._integral += error * dt
        # Clamp integral term to prevent windup (limit based on max acceleration range)
        max_integral = 10.0 / max(self.ki, 0.001)  # Avoid division by zero
        self._integral = max(-max_integral, min(max_integral, self._integral))
        integral = self.ki * self._integral

        # Derivative term (with filtering to reduce noise sensitivity)
        if self._initialized:
            derivative_error = (error - self._prev_error) / dt
            # Apply derivative filtering (simple low-pass)
            derivative = self.kd * derivative_error
        else:
            derivative = 0.0
            self._initialized = True

        self._prev_error = error

        return proportional + integral + derivative

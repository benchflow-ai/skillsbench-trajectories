"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """
    A standard PID (Proportional-Integral-Derivative) controller with anti-windup.

    The controller computes a control output based on the error between
    a setpoint and the measured value, using the formula:
    output = Kp * error + Ki * integral(error) + Kd * derivative(error)
    """

    def __init__(self, kp: float, ki: float, kd: float, integral_limit: float = 10.0):
        """
        Initialize the PID controller with gains.

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
        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """
        Compute the PID control output for a given error.

        Args:
            error: The current error (setpoint - measured_value)
            dt: Time step in seconds

        Returns:
            The control output value
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup clamping
        self._integral += error * dt
        self._integral = max(-self.integral_limit, min(self.integral_limit, self._integral))
        i_term = self.ki * self._integral

        # Derivative term
        if self._prev_error is not None:
            derivative = (error - self._prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        self._prev_error = error

        return p_term + i_term + d_term

"""PID Controller implementation for ACC system."""


class PIDController:
    """
    Proportional-Integral-Derivative controller.

    Implements discrete-time PID control with anti-windup protection.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with gains.

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
        self.first_call = True

    def reset(self):
        """Reset the controller state (integral and derivative terms)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error value (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            float: Control output value
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (avoid derivative kick on first call)
        if self.first_call:
            d_term = 0.0
            self.first_call = False
        else:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative

        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

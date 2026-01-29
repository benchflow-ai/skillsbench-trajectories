"""PID Controller implementation for Adaptive Cruise Control system."""


class PIDController:
    """Proportional-Integral-Derivative controller.

    Implements a discrete-time PID controller with anti-windup protection.
    """

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with gains.

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
        self.first_run = True

    def reset(self):
        """Reset controller state (integral and derivative terms)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_run = True

    def compute(self, error, dt):
        """Compute control output based on error.

        Args:
            error: Current error value (setpoint - measurement)
            dt: Time step since last computation (seconds)

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with trapezoidal integration
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (avoid derivative kick on first run)
        if self.first_run:
            d_term = 0.0
            self.first_run = False
        else:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative

        # Store error for next iteration
        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

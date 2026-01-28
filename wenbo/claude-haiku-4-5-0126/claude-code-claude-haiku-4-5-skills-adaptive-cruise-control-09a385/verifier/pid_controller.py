"""
PID Controller implementation for ACC system speed and distance control.
"""


class PIDController:
    """
    Standard PID controller for error-based feedback control.

    Implements proportional, integral, and derivative terms with
    anti-windup for the integral term.
    """

    def __init__(self, kp, ki, kd, max_output=None, min_output=None):
        """
        Initialize PID controller.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
            max_output (float): Maximum output saturation limit
            min_output (float): Minimum output saturation limit
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.min_output = min_output

        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def reset(self):
        """Reset the PID controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def compute(self, error, dt):
        """
        Compute PID output given current error and time step.

        Args:
            error (float): Current error value (setpoint - measured)
            dt (float): Time step in seconds

        Returns:
            float: PID controller output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        # Apply output saturation if limits are set
        if self.max_output is not None and output > self.max_output:
            output = self.max_output
            # Anti-windup: reduce integral when saturated
            self.integral = (output - p_term - d_term) / (self.ki if self.ki != 0 else 1)

        if self.min_output is not None and output < self.min_output:
            output = self.min_output
            # Anti-windup: reduce integral when saturated
            self.integral = (output - p_term - d_term) / (self.ki if self.ki != 0 else 1)

        return output

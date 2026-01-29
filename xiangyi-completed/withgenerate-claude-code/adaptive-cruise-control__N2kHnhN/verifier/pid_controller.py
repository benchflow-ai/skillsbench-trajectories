"""
PID Controller implementation for ACC system.
"""


class PIDController:
    """
    Proportional-Integral-Derivative controller for feedback control.

    Attributes:
        kp (float): Proportional gain (0-10)
        ki (float): Integral gain (0-5)
        kd (float): Derivative gain (0-5)
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with gains.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Reset controller state (integral and derivative history)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output based on error and time step.

        Args:
            error (float): Current error (setpoint - measurement)
            dt (float): Time step in seconds

        Returns:
            float: Control output command
        """
        # Proportional term: respond immediately to current error
        p_term = self.kp * error

        # Integral term: accumulate error over time to eliminate steady-state error
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term: dampen changes and prevent overshoot
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Update for next iteration
        self.prev_error = error

        # Return total PID output
        return p_term + i_term + d_term

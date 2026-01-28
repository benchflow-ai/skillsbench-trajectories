"""
PID Controller implementation for ACC system.
"""


class PIDController:
    """
    Proportional-Integral-Derivative controller for closed-loop control.
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
        self.last_error = 0.0

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.last_error = 0.0

    def compute(self, error, dt):
        """
        Compute control output given error and timestep.

        Args:
            error: Current error (setpoint - measured value)
            dt: Timestep in seconds

        Returns:
            Control output (float)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self.last_error) / dt
        else:
            d_term = 0.0

        # Update state
        self.last_error = error

        # Compute output
        output = p_term + i_term + d_term

        return output

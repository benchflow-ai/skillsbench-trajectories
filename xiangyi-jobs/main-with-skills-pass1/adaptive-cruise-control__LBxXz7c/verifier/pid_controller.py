"""
PID Controller implementation for ACC speed and distance control.
"""


class PIDController:
    """
    Proportional-Integral-Derivative (PID) controller.

    Implements the standard PID control law:
    u(t) = Kp*e(t) + Ki*∫e(t)dt + Kd*de(t)/dt
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

        # State variables
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Reset the controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID output for given error and time step.

        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            Control output (float)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term (accumulate error over time)
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (rate of change of error)
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Update previous error for next iteration
        self.prev_error = error

        # Total output
        output = p_term + i_term + d_term

        return output

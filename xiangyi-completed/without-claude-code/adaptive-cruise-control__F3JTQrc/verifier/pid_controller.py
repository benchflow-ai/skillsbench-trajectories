"""PID Controller implementation for ACC system."""


class PIDController:
    """
    PID (Proportional-Integral-Derivative) Controller.

    Computes control output based on error signal using three terms:
    - Proportional: responds to current error
    - Integral: responds to accumulated error
    - Derivative: responds to rate of error change
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
        self.reset()

    def reset(self):
        """Reset the controller state (integral term and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error value (setpoint - actual)
            dt: Time step since last computation (seconds)

        Returns:
            float: Control output
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

        # Return combined control output
        return p_term + i_term + d_term

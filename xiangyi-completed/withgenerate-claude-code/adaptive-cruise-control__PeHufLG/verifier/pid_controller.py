"""PID Controller Implementation for Adaptive Cruise Control."""


class PIDController:
    """
    PID (Proportional-Integral-Derivative) controller.

    Computes control output based on error signal using three terms:
    - Proportional: Responds to current error
    - Integral: Responds to accumulated past errors
    - Derivative: Responds to rate of error change
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
        self.reset()

    def reset(self):
        """Reset controller state (integral accumulator and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute control output based on error.

        Args:
            error (float): Current error (setpoint - measured value)
            dt (float): Time step since last update (seconds)

        Returns:
            float: Control output (acceleration command)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term (accumulated error over time)
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (rate of change of error)
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Store current error for next iteration
        self.prev_error = error

        # Return sum of all terms
        return p_term + i_term + d_term

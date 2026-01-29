"""PID Controller implementation for ACC system."""


class PIDController:
    """
    PID (Proportional-Integral-Derivative) controller for closed-loop control.

    Computes control output based on error signal:
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
        """Reset controller state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error signal (setpoint - measured)
            dt: Time step (seconds)

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
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        self.prev_error = error

        # Total control output
        output = p_term + i_term + d_term

        return output

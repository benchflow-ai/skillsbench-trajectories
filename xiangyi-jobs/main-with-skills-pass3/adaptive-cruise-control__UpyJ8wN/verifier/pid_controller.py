"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """PID (Proportional-Integral-Derivative) controller for feedback control.

    This controller computes control output based on error feedback using:
    output = Kp*error + Ki*integral(error) + Kd*derivative(error)
    """

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with gains.

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
        """Reset integral and derivative states."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """Compute control output based on error and timestep.

        Args:
            error (float): Current error value
            dt (float): Time step in seconds

        Returns:
            float: Control output command
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term (accumulate error over time)
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (rate of change of error)
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        d_term = self.kd * derivative

        # Store for next iteration
        self.prev_error = error

        # Total output
        output = p_term + i_term + d_term

        return output

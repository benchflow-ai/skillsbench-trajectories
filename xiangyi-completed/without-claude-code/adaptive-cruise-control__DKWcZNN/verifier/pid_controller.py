"""PID Controller implementation for ACC system."""


class PIDController:
    """PID Controller for closed-loop control.

    Implements a proportional-integral-derivative controller with
    anti-windup protection for the integral term.
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
        self.reset()

    def reset(self):
        """Reset the controller state.

        Clears integral accumulation and previous error.
        """
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """Compute control output based on error.

        Args:
            error: Current error value (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with accumulation
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Update previous error for next iteration
        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

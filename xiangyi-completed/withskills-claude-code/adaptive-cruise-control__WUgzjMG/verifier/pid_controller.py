"""PID Controller implementation for ACC system."""


class PIDController:
    """A simple PID controller for speed and distance control."""

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
        self.integral_error = 0.0
        self.previous_error = 0.0

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self.integral_error = 0.0
        self.previous_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID output based on error and time step.

        Args:
            error (float): Current error (setpoint - measurement)
            dt (float): Time step in seconds

        Returns:
            float: PID output (control signal)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup (limit accumulation)
        self.integral_error += error * dt
        self.integral_error = max(-100, min(100, self.integral_error))  # Clamp integral
        i_term = self.ki * self.integral_error

        # Derivative term
        if dt > 0:
            derivative = (error - self.previous_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Store error for next iteration
        self.previous_error = error

        # Total output
        output = p_term + i_term + d_term

        return output

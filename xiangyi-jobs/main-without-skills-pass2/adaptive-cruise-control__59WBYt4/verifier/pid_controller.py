"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """PID controller for speed and distance control.

    Implements a discrete-time PID controller with anti-windup protection.
    """

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with given gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # Internal state variables
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def reset(self):
        """Reset controller internal state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_call = True

    def compute(self, error, dt):
        """Compute PID control output.

        Args:
            error: Current error value (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (only after first call to avoid spike)
        if self.first_call:
            d_term = 0.0
            self.first_call = False
        else:
            derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
            d_term = self.kd * derivative

        # Update previous error
        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

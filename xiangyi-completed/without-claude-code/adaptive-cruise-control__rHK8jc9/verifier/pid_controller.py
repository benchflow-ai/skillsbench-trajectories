"""PID Controller Implementation for ACC System"""


class PIDController:
    """
    Proportional-Integral-Derivative (PID) Controller

    Implements a standard PID control algorithm with anti-windup protection.
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

        # Internal state variables
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        """Reset the controller's internal state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        """
        Compute control output based on error.

        Args:
            error (float): Current error (setpoint - measurement)
            dt (float): Time step since last computation

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (only after first iteration)
        if self.initialized:
            derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
            d_term = self.kd * derivative
        else:
            d_term = 0.0
            self.initialized = True

        # Update previous error
        self.prev_error = error

        # Return total control output
        return p_term + i_term + d_term

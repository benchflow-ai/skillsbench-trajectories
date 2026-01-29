"""
PID Controller implementation for Adaptive Cruise Control.
"""


class PIDController:
    """
    PID controller for speed and distance control in ACC system.

    Implements proportional-integral-derivative control with anti-windup
    and output saturation.
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

        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        """Reset controller state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error (float): Current error (setpoint - measured value)
            dt (float): Time step in seconds

        Returns:
            float: Control output
        """
        if not self.initialized:
            self.prev_error = error
            self.initialized = True

        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup (clamping)
        self.integral += error * dt
        self.integral = max(-10.0, min(10.0, self.integral))  # Clamp integral
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative
        else:
            d_term = 0.0

        self.prev_error = error

        output = p_term + i_term + d_term
        return output

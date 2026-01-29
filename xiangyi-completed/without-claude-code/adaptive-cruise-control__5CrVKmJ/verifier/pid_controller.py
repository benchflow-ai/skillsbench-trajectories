"""
PID Controller implementation for Adaptive Cruise Control system.
Provides proportional-integral-derivative control for speed and distance regulation.
"""


class PIDController:
    """
    A PID controller for continuous control systems.

    Implements the standard PID control law with integral windup protection.
    """

    def __init__(self, kp, ki, kd, output_min=-8.0, output_max=3.0):
        """
        Initialize the PID controller.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
            output_min (float): Minimum output value (default: -8.0 m/s^2)
            output_max (float): Maximum output value (default: 3.0 m/s^2)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max

        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def reset(self):
        """Reset the controller state (integral term, previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def compute(self, error, dt):
        """
        Compute the control output given an error and time step.

        Args:
            error (float): Current control error (setpoint - measured value)
            dt (float): Time step in seconds

        Returns:
            float: Control output signal, clamped to [output_min, output_max]
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        # Limit integral to prevent windup
        max_integral = self.output_max / (self.ki + 1e-10)
        min_integral = self.output_min / (self.ki + 1e-10)
        self.integral = max(min_integral, min(max_integral, self.integral))
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative
        else:
            d_term = 0.0

        # Compute output and clamp
        output = p_term + i_term + d_term
        output = max(self.output_min, min(self.output_max, output))

        # Update state for next iteration
        self.prev_error = error

        return output

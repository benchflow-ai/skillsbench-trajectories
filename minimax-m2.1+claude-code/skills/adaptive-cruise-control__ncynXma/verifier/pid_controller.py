"""
PID Controller for Adaptive Cruise Control System

This module implements a proportional-integral-derivative controller
used for both speed control and distance control in the ACC system.
"""


class PIDController:
    """
    A PID controller that computes control output based on error input.

    The controller maintains internal state for integral and derivative terms
    and provides methods to reset state and compute new control outputs.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize the PID controller with given gains.

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
        """
        Reset the internal state of the PID controller.

        Clears the integral term and previous error value.
        """
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt, output_limit=None):
        """
        Compute the PID controller output with anti-windup protection.

        Args:
            error (float): The current error (setpoint - measured value)
            dt (float): Time step in seconds
            output_limit (tuple): Optional (min, max) tuple for output saturation

        Returns:
            float: The control output from the PID controller
        """
        # Proportional term
        proportional = self.kp * error

        # Derivative term
        derivative = 0.0
        if dt > 0:
            derivative = self.kd * (error - self.prev_error) / dt

        # Integral term with clamping to prevent excessive windup
        # Only update integral if output would not saturate
        if output_limit is not None and self.ki != 0:
            min_limit, max_limit = output_limit
            # Predict what the output would be
            predicted_output = proportional + self.ki * self.integral + derivative
            if min_limit <= predicted_output <= max_limit:
                # Not saturated, update integral normally
                self.integral += error * dt

        integral = self.ki * self.integral
        raw_output = proportional + integral + derivative

        # Apply saturation limits
        if output_limit is not None:
            min_limit, max_limit = output_limit
            raw_output = max(min_limit, min(max_limit, raw_output))

        # Store error for next iteration
        self.prev_error = error

        return raw_output

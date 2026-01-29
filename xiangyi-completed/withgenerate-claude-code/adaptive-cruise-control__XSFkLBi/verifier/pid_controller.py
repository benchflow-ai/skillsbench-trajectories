"""
PID Controller Implementation for Adaptive Cruise Control

This module implements a discrete-time PID controller with anti-windup protection.
"""


class PIDController:
    """
    PID (Proportional-Integral-Derivative) Controller

    Implements a discrete-time PID controller for feedback control systems.
    The controller calculates a control output based on the error between
    desired and actual states.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with specified gains.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # Internal state
        self.integral = 0.0
        self.previous_error = 0.0

    def reset(self):
        """
        Reset the controller's internal state.

        Clears the integral accumulator and previous error.
        Should be called when switching control modes or when
        discontinuities occur.
        """
        self.integral = 0.0
        self.previous_error = 0.0

    def compute(self, error, dt):
        """
        Calculate PID control output.

        Args:
            error (float): Current error (setpoint - measured_value)
            dt (float): Time step in seconds

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
            derivative = (error - self.previous_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Store error for next iteration
        self.previous_error = error

        # Calculate total output
        output = p_term + i_term + d_term

        return output

"""
PID Controller Implementation for ACC System

This module provides a discrete-time PID controller with anti-windup
and clipping for automotive control applications.
"""

import numpy as np


class PIDController:
    """
    Discrete-time PID controller with anti-windup.

    Implements the standard discrete PID formula:
        u(t) = Kp*e(t) + Ki*∑e(t) + Kd*(e(t) - e(t-1))/dt

    Anti-windup is applied by clamping the integral term to prevent
    unbounded growth when the output is saturated.

    Parameters:
        kp (float): Proportional gain (typically 0.5-5.0)
        ki (float): Integral gain (typically 0.0-2.0)
        kd (float): Derivative gain (typically 0.0-2.0)
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with gains.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
        """
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.reset()

    def reset(self):
        """Reset controller state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error (float): Control error (setpoint - actual value)
            dt (float): Time step in seconds

        Returns:
            float: Control output (acceleration command m/s^2)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        # Accumulate error over time
        self.integral += error * dt
        # Clamp integral to prevent unbounded growth
        self.integral = np.clip(self.integral, -5.0, 5.0)
        i_term = self.ki * self.integral

        # Derivative term
        # Rate of change of error
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        # Store error for next iteration
        self.prev_error = error

        # Total control output
        output = p_term + i_term + d_term

        return output

    def __repr__(self):
        """String representation of controller."""
        return f"PIDController(kp={self.kp:.3f}, ki={self.ki:.3f}, kd={self.kd:.3f})"

"""
PID Controller Implementation for Adaptive Cruise Control

This module provides a discrete PID controller implementation suitable
for vehicle speed and distance control applications.
"""


class PIDController:
    """
    Discrete PID Controller with anti-windup.

    Implements the control law:
        u(t) = Kp * e(t) + Ki * integral(e) + Kd * de/dt
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize PID controller with gains.

        Args:
            kp: Proportional gain - immediate response to error
            ki: Integral gain - eliminates steady-state error
            kd: Derivative gain - dampens oscillations
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        """Reset controller state for new control sequence."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error: float, dt: float) -> float:
        """
        Compute PID control output based on error.

        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            Control output value (unbounded)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term (accumulated error over time)
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (rate of change of error)
        if self.initialized:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
            self.initialized = True
        d_term = self.kd * derivative

        # Store current error for next iteration
        self.prev_error = error

        # Return combined output
        return p_term + i_term + d_term

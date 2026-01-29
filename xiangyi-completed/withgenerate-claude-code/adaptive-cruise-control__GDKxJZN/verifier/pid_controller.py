"""
PID Controller Module for Adaptive Cruise Control System.

This module implements a discrete PID controller with anti-windup
capability for vehicle speed and distance control.
"""


class PIDController:
    """
    Discrete PID Controller implementation.

    The controller computes:
        u(t) = Kp * e(t) + Ki * integral(e) + Kd * de/dt

    where e(t) is the error (setpoint - measured value).
    """

    def __init__(self, kp: float, ki: float, kd: float):
        """
        Initialize PID controller with gains.

        Args:
            kp: Proportional gain - responds to current error magnitude
            ki: Integral gain - eliminates steady-state error over time
            kd: Derivative gain - dampens oscillations and reduces overshoot
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_compute = True

    def reset(self):
        """
        Reset the controller state.

        Clears integral accumulation and derivative history.
        Should be called when switching control modes or after
        significant discontinuities in the controlled system.
        """
        self.integral = 0.0
        self.prev_error = 0.0
        self.first_compute = True

    def compute(self, error: float, dt: float) -> float:
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - measured value).
                   Positive error means measured is below setpoint.
            dt: Time step in seconds since last computation.

        Returns:
            Control output value (e.g., acceleration command).
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term (trapezoidal integration)
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (finite difference)
        if self.first_compute:
            derivative = 0.0
            self.first_compute = False
        else:
            derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative

        # Store error for next derivative calculation
        self.prev_error = error

        # Total control output
        return p_term + i_term + d_term

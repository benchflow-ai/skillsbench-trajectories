"""
PID Controller implementation for Adaptive Cruise Control.

The PID controller computes control outputs based on error feedback using proportional,
integral, and derivative terms.
"""


class PIDController:
    """
    A PID controller that computes control actions based on error measurements.

    The control output is computed as:
        u(t) = Kp * e(t) + Ki * integral(e) + Kd * de/dt

    where:
        - Kp: Proportional gain (acts on current error)
        - Ki: Integral gain (acts on cumulative error)
        - Kd: Derivative gain (acts on rate of change of error)
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize the PID controller with gains.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # Internal state
        self.integral = 0.0  # Accumulated integral error
        self.prev_error = 0.0  # Previous error for derivative calculation

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute the PID control output.

        Args:
            error (float): Current error (setpoint - measured value)
            dt (float): Time step in seconds

        Returns:
            float: Control output (command value)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term (with anti-windup clamping for stability)
        self.integral += error * dt
        # Clamp integral to prevent windup (reasonable bounds for acceleration control)
        self.integral = max(-10.0, min(10.0, self.integral))
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            d_term = self.kd * (error - self.prev_error) / dt
        else:
            d_term = 0.0

        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

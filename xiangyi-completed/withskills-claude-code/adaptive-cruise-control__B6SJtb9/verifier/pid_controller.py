"""
PID Controller Implementation for Adaptive Cruise Control
"""


class PIDController:
    """
    Proportional-Integral-Derivative (PID) controller.

    Computes control output based on error signal using PID control law:
    u(t) = Kp * e(t) + Ki * integral(e(t)) + Kd * de(t)/dt
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
        self.reset()

    def reset(self):
        """Reset internal state of the controller."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error (float): Current error signal (setpoint - measurement)
            dt (float): Time step since last computation (seconds)

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Update previous error
        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

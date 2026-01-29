"""PID Controller for Adaptive Cruise Control System."""


class PIDController:
    """
    Proportional-Integral-Derivative (PID) controller.

    The PID controller computes a control output based on the error between
    the desired setpoint and the measured process variable.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - measurement)
            dt: Time step since last computation (seconds)

        Returns:
            float: Control output value
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term
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

"""PID Controller Implementation for Adaptive Cruise Control"""


class PIDController:
    """
    Proportional-Integral-Derivative (PID) controller.

    The PID controller computes a control signal based on the error between
    a desired setpoint and a measured process variable.
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
        self.is_first_call = True

    def reset(self):
        """Reset the controller state (integral term and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.is_first_call = True

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - measurement)
            dt: Time step since last computation (seconds)

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term (accumulate error over time)
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term (rate of change of error)
        if self.is_first_call:
            d_term = 0.0
            self.is_first_call = False
        else:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative

        # Update previous error for next iteration
        self.prev_error = error

        # Compute total control output
        output = p_term + i_term + d_term

        return output

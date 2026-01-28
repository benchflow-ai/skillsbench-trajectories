"""PID Controller implementation for ACC system."""


class PIDController:
    """
    Proportional-Integral-Derivative controller.

    The PID controller computes a control output based on the error
    between a setpoint and measured value.
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
        """Reset the controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.is_first_call = True

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error: Current error (setpoint - measured_value)
            dt: Time step since last computation

        Returns:
            float: Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if self.is_first_call:
            d_term = 0.0
            self.is_first_call = False
        else:
            derivative = (error - self.prev_error) / dt
            d_term = self.kd * derivative

        # Store error for next iteration
        self.prev_error = error

        # Compute total output
        output = p_term + i_term + d_term

        return output

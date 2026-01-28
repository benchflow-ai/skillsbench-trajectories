class PIDController:
    """
    A PID (Proportional-Integral-Derivative) controller.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.reset()

    def reset(self):
        """Reset the internal state of the PID controller."""
        self.integral = 0.0
        self.previous_error = 0.0

    def compute(self, error, dt):
        """
        Compute the control output based on the error.

        Args:
            error: The error signal (setpoint - measured_value)
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
        derivative = (error - self.previous_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative

        # Update previous error
        self.previous_error = error

        # Return control output
        return p_term + i_term + d_term

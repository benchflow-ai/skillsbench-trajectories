class PIDController:
    """PID controller with anti-windup clamping."""

    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = None

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error, dt):
        """Compute PID output.

        Args:
            error: Current error (setpoint - measurement).
            dt: Time step in seconds.

        Returns:
            Control output as float.
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup clamping
        self.integral += error * dt
        # Clamp integral to prevent windup (max integral contribution = 10.0)
        max_integral = 10.0 / (self.ki + 1e-10)
        self.integral = max(-max_integral, min(max_integral, self.integral))
        i_term = self.ki * self.integral

        # Derivative term
        if self.prev_error is not None:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        self.prev_error = error

        return p_term + i_term + d_term

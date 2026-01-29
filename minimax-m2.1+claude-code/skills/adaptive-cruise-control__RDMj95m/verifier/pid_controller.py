"""PID Controller Implementation for Adaptive Cruise Control System"""

class PIDController:
    """
    Proportional-Integral-Derivative (PID) Controller

    Computes control output based on error signal with proportional,
    integral, and derivative terms.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with gain parameters.

        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.prev_error = 0.0
        self.integral = 0.0
        self.reset()

    def reset(self):
        """Reset controller state (integral and previous error)"""
        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, error, dt):
        """
        Compute PID control output.

        Args:
            error (float): Current error signal (setpoint - measured value)
            dt (float): Time step in seconds

        Returns:
            float: Control output
        """
        # Integral term accumulation
        self.integral += error * dt

        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0

        # PID output
        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        # Update previous error
        self.prev_error = error

        return output

"""PID Controller implementation for vehicle control systems."""


class PIDController:
    """
    PID (Proportional-Integral-Derivative) Controller.

    A feedback control mechanism that calculates an error value as the difference
    between a desired setpoint and a measured process variable, then applies a
    correction based on proportional, integral, and derivative terms.
    """

    def __init__(self, kp, ki, kd):
        """
        Initialize PID controller with gains.

        Args:
            kp (float): Proportional gain - determines reaction to current error
            ki (float): Integral gain - determines reaction to accumulated error
            kd (float): Derivative gain - determines reaction to rate of error change
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.reset()

    def reset(self):
        """Reset the controller's internal state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """
        Compute PID output based on current error and time step.

        The PID output is calculated as:
        output = Kp * error + Ki * integral(error) + Kd * d(error)/dt

        Args:
            error (float): Current error value (setpoint - measured_value)
            dt (float): Time step since last update (seconds)

        Returns:
            float: Control output value
        """
        # Proportional term - immediate response to current error
        p_term = self.kp * error

        # Integral term - accumulate error over time to eliminate steady-state error
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term - predict future error based on rate of change
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Update previous error for next iteration
        self.prev_error = error

        # Calculate total output
        output = p_term + i_term + d_term

        return output

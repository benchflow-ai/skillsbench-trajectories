"""PID Controller Implementation for Adaptive Cruise Control"""


class PIDController:
    """PID controller for feedback control systems."""

    def __init__(self, kp, ki, kd):
        """Initialize PID controller with tuning parameters.

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
        """Reset internal state (integral and previous error)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt, output_limits=None):
        """Compute PID control output.

        Args:
            error: Current error value (setpoint - measurement)
            dt: Time step since last computation
            output_limits: Optional tuple (min, max) for output clamping and anti-windup

        Returns:
            float: Control output value
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative

        # Calculate output
        output = p_term + i_term + d_term

        # Apply anti-windup: back-calculate integral if output is saturated
        if output_limits is not None:
            min_limit, max_limit = output_limits
            if output > max_limit:
                # Back-calculate integral to prevent windup
                if self.ki > 1e-6:
                    self.integral = (max_limit - p_term - d_term) / self.ki
                output = max_limit
            elif output < min_limit:
                if self.ki > 1e-6:
                    self.integral = (min_limit - p_term - d_term) / self.ki
                output = min_limit

        # Update previous error
        self.prev_error = error

        return output

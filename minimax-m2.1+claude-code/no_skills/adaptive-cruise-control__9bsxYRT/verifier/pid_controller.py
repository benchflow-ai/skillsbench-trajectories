"""PID Controller implementation for Adaptive Cruise Control."""

class PIDController:
    """A proportional-integral-derivative controller with anti-windup."""

    def __init__(self, kp: float = 0.0, ki: float = 0.0, kd: float = 0.0,
                 output_limits: tuple[float, float] = (float('-inf'), float('inf'))):
        """
        Initialize the PID controller with given gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_limits: Tuple of (min, max) output limits
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min, self.output_max = output_limits
        self.reset()

    def reset(self):
        """Reset the controller state (integral and derivative terms)."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        """
        Compute the PID control output.

        Args:
            error: The current error value (target - actual)
            dt: Time step in seconds

        Returns:
            Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term - only accumulate if not saturated
        # This is a simple anti-windup: don't let integral grow when output is saturated
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term on error
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative

        # Store error for next iteration
        self.prev_error = error

        # Compute raw output
        output = p_term + i_term + d_term

        # Apply output limits
        output = max(self.output_min, min(self.output_max, output))

        # Anti-windup: if output is saturated, freeze integral to prevent windup
        # Check if raw output would have been outside limits
        if p_term + i_term + d_term > self.output_max:
            # Undo the integral accumulation for this step
            self.integral -= error * dt
        elif p_term + i_term + d_term < self.output_min:
            self.integral -= error * dt

        return output

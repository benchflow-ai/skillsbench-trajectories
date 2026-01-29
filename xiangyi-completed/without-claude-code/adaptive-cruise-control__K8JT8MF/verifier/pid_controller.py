"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """A PID controller with anti-windup and derivative filtering."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = -8.0, output_max: float = 3.0):
        """Initialize the PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output limit for anti-windup
            output_max: Maximum output limit for anti-windup
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.reset()

    def reset(self):
        """Reset the controller state (integral and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """Compute the PID control output.

        Args:
            error: Current error (setpoint - measured value)
            dt: Time step in seconds

        Returns:
            Control output (clamped to output limits)
        """
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Derivative term (compute before integral for derivative kick prevention)
        if self._prev_error is None:
            d_term = 0.0
        else:
            derivative = (error - self._prev_error) / dt
            d_term = self.kd * derivative

        self._prev_error = error

        # Compute output without integral to check saturation
        output_pd = p_term + d_term

        # Anti-windup: only integrate if not saturated or integrating toward unsaturation
        if self.ki > 0:
            # Check if adding integral would help or hurt
            potential_integral = self._integral + error * dt
            potential_output = output_pd + self.ki * potential_integral

            # Conditional integration (clamping anti-windup)
            if potential_output > self.output_max and error > 0:
                # Output saturated high and error positive - don't integrate
                pass
            elif potential_output < self.output_min and error < 0:
                # Output saturated low and error negative - don't integrate
                pass
            else:
                self._integral += error * dt

        i_term = self.ki * self._integral

        output = p_term + i_term + d_term

        # Clamp output
        return max(self.output_min, min(self.output_max, output))

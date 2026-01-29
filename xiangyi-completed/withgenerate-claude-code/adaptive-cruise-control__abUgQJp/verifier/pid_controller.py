"""PID Controller implementation for Adaptive Cruise Control."""


class PIDController:
    """
    A standard PID (Proportional-Integral-Derivative) controller.

    The controller computes the control output as:
        u(t) = Kp * e(t) + Ki * integral(e(t)dt) + Kd * de(t)/dt

    Attributes:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
    """

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float = None, output_max: float = None):
        """
        Initialize PID controller with gains.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Minimum output limit for anti-windup (optional)
            output_max: Maximum output limit for anti-windup (optional)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Reset the controller state (integral accumulator and previous error)."""
        self._integral = 0.0
        self._prev_error = None

    def compute(self, error: float, dt: float) -> float:
        """
        Compute the PID control output with anti-windup.

        Args:
            error: Current error (setpoint - measured_value)
            dt: Time step in seconds

        Returns:
            Control output (float)
        """
        # Proportional term
        p_term = self.kp * error

        # Compute tentative integral
        tentative_integral = self._integral + error * dt

        # Derivative term
        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt

        self._prev_error = error

        # Compute tentative output
        i_term = self.ki * tentative_integral
        output = p_term + i_term + d_term

        # Anti-windup: only update integral if output is not saturated
        # or if the integral change would help reduce saturation
        saturated_high = self.output_max is not None and output > self.output_max
        saturated_low = self.output_min is not None and output < self.output_min

        if saturated_high:
            # Only allow integral to decrease (error < 0)
            if error < 0:
                self._integral = tentative_integral
            # Clamp output
            output = self.output_max
        elif saturated_low:
            # Only allow integral to increase (error > 0)
            if error > 0:
                self._integral = tentative_integral
            # Clamp output
            output = self.output_min
        else:
            # Not saturated, update integral normally
            self._integral = tentative_integral

        return output

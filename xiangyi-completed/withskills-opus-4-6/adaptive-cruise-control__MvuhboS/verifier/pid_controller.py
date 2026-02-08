"""PID Controller with anti-windup for Adaptive Cruise Control."""


class PIDController:
    """Discrete-time PID controller with integral anti-windup."""

    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0
        self._first_call = True

    def reset(self):
        """Clear controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self._first_call = True

    def compute(self, error, dt):
        """Compute control output given error and timestep.

        Args:
            error: setpoint - measured_value
            dt: timestep in seconds

        Returns:
            float: control output (clamped if limits set)
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup (conditional integration)
        candidate_integral = self.integral + error * dt
        candidate_i_term = self.ki * candidate_integral

        # Derivative term (skip on first call to avoid spike)
        if self._first_call:
            derivative = 0.0
            self._first_call = False
        else:
            derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        self.prev_error = error

        # Compute candidate output to check saturation
        candidate_output = p_term + candidate_i_term + d_term

        # Anti-windup: only update integral if output is not saturated,
        # or if the integral is moving toward zero
        saturated = False
        if self.output_min is not None and candidate_output < self.output_min:
            saturated = True
        if self.output_max is not None and candidate_output > self.output_max:
            saturated = True

        if not saturated or (error * self.integral < 0):
            # Not saturated, or error is pushing integral back toward zero
            self.integral = candidate_integral

        i_term = self.ki * self.integral
        output = p_term + i_term + d_term

        # Output clamping
        if self.output_min is not None:
            output = max(output, self.output_min)
        if self.output_max is not None:
            output = min(output, self.output_max)

        return output


class PIDController:
    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Clear controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def initialize(self, current_error, current_integral=0.0):
        """Initialize controller state to avoid derivative kicks on mode switch."""
        self.prev_error = current_error
        self.integral = current_integral

    def compute(self, error, dt):
        """Compute control output given error and timestep."""
        # Proportional term
        p_term = self.kp * error

        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        self.prev_error = error

        # Total output
        output = p_term + i_term + d_term

        # Output clamping and Anti-windup
        if self.output_min is not None and output < self.output_min:
            output = self.output_min
            # Anti-windup: if output is clamped at min and error is negative (trying to go lower),
            # stop integrating (or subtract the addition).
            # Easier strategy: clamp integral so it doesn't grow indefinitely?
            # Or conditional integration:
            if error < 0:
                self.integral -= error * dt # Undo integration
        elif self.output_max is not None and output > self.output_max:
            output = self.output_max
            if error > 0:
                self.integral -= error * dt # Undo integration

        return output

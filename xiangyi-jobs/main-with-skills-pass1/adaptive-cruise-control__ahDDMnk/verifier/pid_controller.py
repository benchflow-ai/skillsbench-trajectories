"""PID controller implementation."""


class PIDController:
    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        """Clear controller state."""
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        """Compute control output given error and timestep."""
        if dt <= 0:
            return 0.0

        # Proportional term
        p_term = self.kp * error

        # Integral term (conditional integration for basic anti-windup)
        proposed_integral = self.integral + error * dt
        i_term = self.ki * proposed_integral

        # Derivative term
        derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative

        output = p_term + i_term + d_term

        clamped = False
        if self.output_min is not None and output < self.output_min:
            output = self.output_min
            clamped = True
        if self.output_max is not None and output > self.output_max:
            output = self.output_max
            clamped = True

        if not clamped:
            self.integral = proposed_integral

        self.prev_error = error
        return output

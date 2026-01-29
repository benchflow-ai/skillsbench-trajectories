class PIDController:
    def __init__(self, kp, ki, kd, output_min=None, output_max=None):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_min = output_min
        self.output_max = output_max
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0

        # Proportional
        p_term = self.kp * error

        # Derivative
        if self.initialized:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
            self.initialized = True

        d_term = self.kd * derivative

        # Tentative integral for simple anti-windup
        tentative_integral = self.integral + error * dt
        i_term = self.ki * tentative_integral

        output_unclamped = p_term + i_term + d_term

        if self.output_min is not None and output_unclamped < self.output_min:
            output = self.output_min
            # Only accept integral if it helps move back toward range
            if error > 0:
                self.integral = tentative_integral
        elif self.output_max is not None and output_unclamped > self.output_max:
            output = self.output_max
            if error < 0:
                self.integral = tentative_integral
        else:
            output = output_unclamped
            self.integral = tentative_integral

        self.prev_error = error
        return output

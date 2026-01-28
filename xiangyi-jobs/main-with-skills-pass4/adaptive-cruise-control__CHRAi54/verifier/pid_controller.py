class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_min = None
        self.output_max = None
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0

        p_term = self.kp * error
        candidate_integral = self.integral + error * dt
        i_term = self.ki * candidate_integral
        d_term = self.kd * ((error - self.prev_error) / dt)
        self.prev_error = error

        output = p_term + i_term + d_term

        if self.output_min is not None or self.output_max is not None:
            min_out = self.output_min if self.output_min is not None else output
            max_out = self.output_max if self.output_max is not None else output
            if output < min_out and error < 0:
                return min_out
            if output > max_out and error > 0:
                return max_out

        self.integral = candidate_integral
        return output

class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.integral = 0.0
        self.last_error = None
        self.output_limits = None

    def reset(self):
        self.integral = 0.0
        self.last_error = None

    def compute(self, error, dt):
        if dt <= 0.0:
            return 0.0

        derivative = 0.0 if self.last_error is None else (error - self.last_error) / dt
        integral_candidate = self.integral + error * dt

        output = (self.kp * error) + (self.ki * integral_candidate) + (self.kd * derivative)

        if self.output_limits is not None:
            min_out, max_out = self.output_limits
            if output > max_out:
                output = max_out
                if error < 0.0:
                    self.integral = integral_candidate
            elif output < min_out:
                output = min_out
                if error > 0.0:
                    self.integral = integral_candidate
            else:
                self.integral = integral_candidate
        else:
            self.integral = integral_candidate

        self.last_error = error
        return output

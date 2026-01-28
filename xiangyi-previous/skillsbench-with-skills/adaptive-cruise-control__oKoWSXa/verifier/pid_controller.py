class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False
        self.output_min = None
        self.output_max = None

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.initialized = False

    def compute(self, error, dt):
        if dt <= 0:
            return self.kp * error

        if not self.initialized:
            self.prev_error = error
            self.initialized = True

        self.integral += error * dt
        derivative = (error - self.prev_error) / dt

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        if self.output_min is not None and output < self.output_min:
            self.integral -= error * dt
            output = self.output_min
        elif self.output_max is not None and output > self.output_max:
            self.integral -= error * dt
            output = self.output_max

        self.prev_error = error

        return output

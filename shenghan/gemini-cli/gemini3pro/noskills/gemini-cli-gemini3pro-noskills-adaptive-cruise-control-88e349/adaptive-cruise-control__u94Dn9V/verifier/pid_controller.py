class PIDController:
    def __init__(self, kp, ki, kd, output_limits=(None, None)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0
        self.min_out, self.max_out = output_limits

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error, dt):
        # P Term
        p_term = self.kp * error
        
        # D Term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        
        # Tentative Output for Anti-Windup Check
        # We need to know if we WOULD saturate with the new integral
        # But integral depends on history.
        
        # Conditional Integration:
        # Calculate what the output WOULD be if we integrated
        tentative_integral = self.integral + error * dt
        tentative_out = p_term + (self.ki * tentative_integral) + d_term
        
        # Check saturation
        saturated = False
        if self.max_out is not None and tentative_out > self.max_out:
            saturated = True
            clamped_out = self.max_out
        elif self.min_out is not None and tentative_out < self.min_out:
            saturated = True
            clamped_out = self.min_out
        else:
            clamped_out = tentative_out
            
        # Update Integral ONLY if NOT saturated OR if error opposes saturation
        # If saturated high (output > max) and error > 0 (trying to increase), Don't integrate.
        # If saturated high and error < 0 (trying to decrease), Integrate (help unsaturate).
        
        if not saturated:
            self.integral = tentative_integral
        elif (clamped_out == self.max_out and error < 0):
            self.integral = tentative_integral
        elif (clamped_out == self.min_out and error > 0):
            self.integral = tentative_integral
        # Else: keep self.integral as is (clamp)
        
        # Final Output Calculation with actual integral
        output = p_term + (self.ki * self.integral) + d_term
        
        # Final Clamp
        if self.max_out is not None and output > self.max_out:
            output = self.max_out
        if self.min_out is not None and output < self.min_out:
            output = self.min_out
            
        self.prev_error = error
        return output

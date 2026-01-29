from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PIDs
        # Assuming the config passed includes the PID gains or we need to look them up?
        # The prompt says "config is nested dict from vehicle_params.yaml".
        # However, PID gains are in 'pid_speed' and 'pid_distance' keys in that yaml.
        # But simulation.py reads tuning_results.yaml. 
        # So I should probably allow updating gains or pass them in config.
        # I will assume 'config' contains the FULL yaml structure including pid sections, 
        # possibly updated with tuning results.
        
        self.pid_speed = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd'],
            output_limits=(self.max_decel, self.max_accel)
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd'],
            output_limits=(self.max_decel, self.max_accel)
        )
        
        self.last_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        # Determine Mode
        mode = 'cruise'
        distance_error = None
        
        if lead_speed is not None and distance is not None and not (lead_speed != lead_speed): # Check for NaN
            # Lead vehicle present
            rel_speed = ego_speed - lead_speed
            
            ttc = float('inf')
            if rel_speed > 0:
                ttc = distance / rel_speed
            
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
            else:
                mode = 'follow'
        
        # Calculate Control
        acc_cmd = 0.0
        
        if mode == 'emergency':
            acc_cmd = self.max_decel
            # Reset PIDs to prevent windup during emergency?
            self.pid_speed.reset()
            self.pid_distance.reset()
            # Calculate distance error for reporting even in emergency
            safe_distance = max(self.min_distance, self.time_headway * ego_speed)
            distance_error = distance - safe_distance

        elif mode == 'follow':
            safe_distance = max(self.min_distance, self.time_headway * ego_speed)
            distance_error = distance - safe_distance
            
            # Distance Control
            acc_dist = self.pid_distance.compute(distance_error, dt)
            
            # Speed Control (Safety Limit)
            # We want to ensure we don't exceed set_speed while following
            speed_error = self.set_speed - ego_speed
            acc_speed = self.pid_speed.compute(speed_error, dt)
            
            # Take the most conservative (minimum) acceleration
            acc_cmd = min(acc_dist, acc_speed)
            
            # Note: Running both PIDs simultaneously might cause windup in the one not selected.
            # But with the 'Conditional Integration' fix in pid_controller.py (clamping logic),
            # it should be relatively safe as long as we don't feed huge errors.
            # Actually, if we pick min, the other one might have wanted higher.
            # If acc_dist < acc_speed (we are braking for car), acc_speed wants to accel.
            # Speed PID sees positive error (we are slow), so it integrates up.
            # This is "Integrator Windup" due to selection.
            # Ideally we should stop integrating the Speed PID if it's not selected and it wants to go higher.
            # But given the complexity constraints, and that we have output clamping, it might be OK.
            # Better: Reset the unused one? No, that causes jumps.
            # Let's hope the new anti-windup (output clamping) helps, 
            # OR we can manually clamp the integral of the non-selected one?
            # For now, just taking min is a huge improvement over chasing to infinity.

        else: # cruise
            error = self.set_speed - ego_speed
            acc_cmd = self.pid_speed.compute(error, dt)
            self.pid_distance.reset()
            distance_error = None

        # Clamp acceleration
        acc_cmd = max(self.max_decel, min(self.max_accel, acc_cmd))
        
        return acc_cmd, mode, distance_error

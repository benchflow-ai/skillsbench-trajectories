
import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.vehicle_params = config['vehicle']
        self.acc_settings = config['acc_settings']
        
        # Initialize PIDs
        # Speed PID
        pid_speed_cfg = config['pid_speed']
        self.pid_speed = PIDController(
            kp=pid_speed_cfg['kp'],
            ki=pid_speed_cfg['ki'],
            kd=pid_speed_cfg['kd'],
            output_min=self.vehicle_params['max_deceleration'],
            output_max=self.vehicle_params['max_acceleration']
        )
        
        # Distance PID
        pid_dist_cfg = config['pid_distance']
        self.pid_distance = PIDController(
            kp=pid_dist_cfg['kp'],
            ki=pid_dist_cfg['ki'],
            kd=pid_dist_cfg['kd'],
            output_min=self.vehicle_params['max_deceleration'],
            output_max=self.vehicle_params['max_acceleration']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on sensor inputs.
        
        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s) or None/NaN
            distance: Distance to lead vehicle (m) or None/NaN
            dt: Time step (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        mode = 'cruise'
        accel_cmd = 0.0
        dist_error = None
        
        # Check if lead vehicle is present
        # In pandas, NaN is standard for missing data, but here we might get None or float('nan')
        has_lead = False
        if lead_speed is not None and distance is not None:
            try:
                if not math.isnan(lead_speed) and not math.isnan(distance):
                    has_lead = True
            except TypeError:
                pass # Not a number
        
        if not has_lead:
            mode = 'cruise'
            # Cruise Control: Maintain set speed
            target_speed = self.acc_settings['set_speed']
            error = target_speed - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
            # Reset distance PID to prevent windup when not in use
            self.pid_distance.reset()
            
        else:
            # Calculate TTC
            # TTC = distance / (ego_speed - lead_speed)
            relative_speed = ego_speed - lead_speed
            ttc = float('inf')
            if relative_speed > 0:
                ttc = distance / relative_speed
                
            if ttc < self.acc_settings['emergency_ttc_threshold']:
                mode = 'emergency'
                # Emergency Braking: Max deceleration
                accel_cmd = self.vehicle_params['max_deceleration']
                # Reset PIDs
                self.pid_speed.reset()
                self.pid_distance.reset()
                
                # Calculate distance error for reporting even in emergency
                safe_dist = self.calculate_safe_distance(ego_speed)
                dist_error = distance - safe_dist
                
            else:
                mode = 'follow'
                # Follow Mode: Maintain safe distance
                safe_dist = self.calculate_safe_distance(ego_speed)
                
                # Error defined as (current - desired). 
                # If current > desired, we are too far, error > 0 -> accelerate.
                # If current < desired, we are too close, error < 0 -> decelerate.
                error = distance - safe_dist
                dist_error = error
                
                accel_cmd = self.pid_distance.compute(error, dt)
                # Reset speed PID
                self.pid_speed.reset()

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.vehicle_params['max_deceleration'], 
                        min(accel_cmd, self.vehicle_params['max_acceleration']))
        
        return accel_cmd, mode, dist_error

    def calculate_safe_distance(self, ego_speed):
        """Calculate desired safe following distance."""
        # desired_distance = speed * time_headway + min_distance
        return ego_speed * self.acc_settings['time_headway'] + self.acc_settings['min_distance']

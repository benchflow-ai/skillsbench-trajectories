from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']

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
        
        self.filtered_distance = None
        self.filtered_lead_speed = None
        self.alpha = 0.1 # Filter constant

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        acceleration_cmd = 0.0
        distance_error = None

        # Always compute speed-based acceleration
        speed_error = self.set_speed - ego_speed
        accel_speed = self.pid_speed.compute(speed_error, dt)

        if distance is not None and not (isinstance(distance, float) and distance != distance):
            # Filter distance and lead speed
            if self.filtered_distance is None:
                self.filtered_distance = distance
                self.filtered_lead_speed = lead_speed
            else:
                self.filtered_distance = self.alpha * distance + (1 - self.alpha) * self.filtered_distance
                self.filtered_lead_speed = self.alpha * lead_speed + (1 - self.alpha) * self.filtered_lead_speed
            
            distance = self.filtered_distance
            lead_speed = self.filtered_lead_speed

            # Lead vehicle detected
            safe_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - safe_distance
            
            relative_speed = ego_speed - lead_speed
            ttc = float('inf')
            if relative_speed > 0:
                ttc = distance / relative_speed

            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_decel
                self.pid_speed.reset()
                self.pid_distance.reset()
            else:
                mode = 'follow'
                accel_dist = self.pid_distance.compute(distance_error, dt)
                acceleration_cmd = min(accel_speed, accel_dist)
        else:
            # No lead vehicle
            mode = 'cruise'
            acceleration_cmd = accel_speed
            self.pid_distance.reset()
            self.filtered_distance = None
            self.filtered_lead_speed = None

        # Apply acceleration limits
        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))

        return acceleration_cmd, mode, distance_error

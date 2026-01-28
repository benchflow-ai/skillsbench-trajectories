
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_gap = config['acc_settings']['min_distance']
        self.ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_accel = config['vehicle']['max_acceleration']
        self.max_decel = config['vehicle']['max_deceleration']
        
        # Initialize PID controllers
        self.pid_speed = PIDController(
            config['pid_speed']['kp'], 
            config['pid_speed']['ki'], 
            config['pid_speed']['kd']
        )
        self.pid_distance = PIDController(
            config['pid_distance']['kp'], 
            config['pid_distance']['ki'], 
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on ACC logic.
        
        Args:
            ego_speed: Current speed of the ego vehicle (m/s)
            lead_speed: Current speed of the lead vehicle (m/s) or None
            distance: Current distance to the lead vehicle (m) or None
            dt: Timestep (s)
            
        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        # Calculate TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        # Mode Selection
        if lead_speed is None or distance is None:
            mode = 'cruise'
        elif ttc is not None and ttc < self.ttc_threshold:
            mode = 'emergency'
        else:
            mode = 'follow'

        # Control Logic
        acceleration_cmd = 0.0
        distance_error = None
        
        if mode == 'cruise':
            error = self.set_speed - ego_speed
            acceleration_cmd = self.pid_speed.compute(error, dt)
            self.pid_distance.reset()
        elif mode == 'emergency':
            acceleration_cmd = self.max_decel
            # Still compute target distance for error reporting if needed
            target_distance = ego_speed * self.time_headway + self.min_gap
            distance_error = distance - target_distance
            self.pid_speed.reset()
            self.pid_distance.reset()
        elif mode == 'follow':
            target_distance = ego_speed * self.time_headway + self.min_gap
            distance_error = distance - target_distance
            acceleration_cmd = self.pid_distance.compute(distance_error, dt)
            self.pid_speed.reset()
            
        # Clamp acceleration
        acceleration_cmd = max(self.max_decel, min(acceleration_cmd, self.max_accel))
        
        return acceleration_cmd, mode, distance_error

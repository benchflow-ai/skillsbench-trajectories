from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_gap = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

        self.prev_distance = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        if lead_speed is None or (isinstance(lead_speed, str) and lead_speed == ''):
            lead_speed = None

        if lead_speed is None:
            mode = 'cruise'
            error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(error, dt)
            distance_error = None
        else:
            if distance is None or (isinstance(distance, str) and distance == ''):
                distance = self.prev_distance if self.prev_distance is not None else 50.0

            desired_distance = self.min_gap + ego_speed * self.time_headway
            distance_error = desired_distance - distance

            ttc = distance / (ego_speed - lead_speed) if ego_speed > lead_speed else float('inf')

            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_deceleration
            else:
                mode = 'follow'
                acceleration_cmd = self.distance_pid.compute(distance_error, dt)

        acceleration_cmd = max(self.max_deceleration,
                              min(self.max_acceleration, acceleration_cmd))

        if distance is not None:
            self.prev_distance = distance

        return acceleration_cmd, mode, distance_error

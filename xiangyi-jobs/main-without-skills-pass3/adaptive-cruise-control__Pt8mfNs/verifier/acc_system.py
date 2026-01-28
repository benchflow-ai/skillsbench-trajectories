from pid_controller import PIDController
import math

class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_cfg = config['acc_settings']
        veh_cfg = config['vehicle']
        self.set_speed = acc_cfg['set_speed']
        self.time_headway = acc_cfg['time_headway']
        self.min_distance = acc_cfg['min_distance']
        self.emergency_ttc_threshold = acc_cfg['emergency_ttc_threshold']
        self.max_acceleration = veh_cfg['max_acceleration']
        self.max_deceleration = veh_cfg['max_deceleration']

        pid_speed_cfg = config['pid_speed']
        pid_distance_cfg = config['pid_distance']
        self.pid_speed = PIDController(pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd'])
        self.pid_distance = PIDController(pid_distance_cfg['kp'], pid_distance_cfg['ki'], pid_distance_cfg['kd'])

    def compute(self, ego_speed, lead_speed, distance, dt):
        # No lead vehicle detected
        if lead_speed is None or distance is None:
            self.pid_distance.reset()
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            return accel_cmd, mode, None

        # Lead vehicle detected
        relative_speed = ego_speed - lead_speed
        if relative_speed > 0:
            ttc = distance / relative_speed if relative_speed > 1e-3 else math.inf
        else:
            ttc = math.inf

        if ttc < self.emergency_ttc_threshold:
            self.pid_speed.reset()
            self.pid_distance.reset()
            mode = 'emergency'
            accel_cmd = self.max_deceleration
            distance_error = distance - max(self.min_distance, self.time_headway * ego_speed)
            return accel_cmd, mode, distance_error

        # Following mode
        mode = 'follow'
        desired_distance = max(self.min_distance, self.time_headway * ego_speed)
        distance_error = distance - desired_distance
        # distance PID outputs speed correction relative to lead
        speed_correction = self.pid_distance.compute(distance_error, dt)
        target_speed = min(self.set_speed, max(0.0, lead_speed + speed_correction))
        accel_cmd = self.pid_speed.compute(target_speed - ego_speed, dt)
        return accel_cmd, mode, distance_error

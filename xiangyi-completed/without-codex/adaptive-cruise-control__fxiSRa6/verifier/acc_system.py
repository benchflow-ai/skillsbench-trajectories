from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        settings = config['acc_settings']
        vehicle = config['vehicle']
        self.set_speed = float(settings['set_speed'])
        self.time_headway = float(settings['time_headway'])
        self.min_distance = float(settings['min_distance'])
        self.emergency_ttc = float(settings['emergency_ttc_threshold'])
        self.max_acc = float(vehicle['max_acceleration'])
        self.max_dec = float(vehicle['max_deceleration'])

        pid_speed_cfg = config['pid_speed']
        pid_dist_cfg = config['pid_distance']
        self.pid_speed = PIDController(pid_speed_cfg['kp'], pid_speed_cfg['ki'], pid_speed_cfg['kd'])
        self.pid_distance = PIDController(pid_dist_cfg['kp'], pid_dist_cfg['ki'], pid_dist_cfg['kd'])
        self._prev_mode = None
        self._safety_ttc = 5.0

    def _clamp(self, value):
        if value > self.max_acc:
            return self.max_acc
        if value < self.max_dec:
            return self.max_dec
        return value

    def _reset_on_mode_change(self, mode):
        if self._prev_mode != mode:
            self.pid_speed.reset()
            self.pid_distance.reset()

    def compute(self, ego_speed, lead_speed, distance, dt):
        if lead_speed is None or distance is None:
            mode = 'cruise'
            self._reset_on_mode_change(mode)
            acc_cmd = self.pid_speed.compute(self.set_speed - ego_speed, dt)
            acc_cmd = self._clamp(acc_cmd)
            self._prev_mode = mode
            return acc_cmd, mode, None

        relative_speed = ego_speed - lead_speed
        if relative_speed > 0.0 and distance > 0.0:
            ttc = distance / relative_speed
        else:
            ttc = float('inf')

        desired_distance = self.min_distance + (self.time_headway * ego_speed)
        distance_error = distance - desired_distance

        if distance <= self.min_distance or ttc < self.emergency_ttc:
            mode = 'emergency'
            self._reset_on_mode_change(mode)
            acc_cmd = self.max_dec
        else:
            mode = 'follow'
            self._reset_on_mode_change(mode)
            speed_correction = self.pid_distance.compute(distance_error, dt)
            gap_speed = max(0.0, (distance - self.min_distance) / self.time_headway)
            target_speed = min(self.set_speed, lead_speed + speed_correction, gap_speed)
            if ttc < self._safety_ttc:
                target_speed *= max(0.0, ttc / self._safety_ttc)
            if target_speed < 0.0:
                target_speed = 0.0
            acc_cmd = self.pid_speed.compute(target_speed - ego_speed, dt)

        acc_cmd = self._clamp(acc_cmd)
        self._prev_mode = mode
        return acc_cmd, mode, distance_error

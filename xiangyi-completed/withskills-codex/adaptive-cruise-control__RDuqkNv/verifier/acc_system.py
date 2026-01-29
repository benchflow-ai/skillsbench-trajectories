from pid_controller import PIDController


def _clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_settings = config.get('acc_settings', {})
        vehicle = config.get('vehicle', {})
        pid_speed_cfg = config.get('pid_speed', {})
        pid_dist_cfg = config.get('pid_distance', {})

        self.set_speed = float(acc_settings.get('set_speed', 30.0))
        self.time_headway = float(acc_settings.get('time_headway', 1.5))
        self.min_distance = float(acc_settings.get('min_distance', 10.0))
        self.emergency_ttc_threshold = float(
            acc_settings.get('emergency_ttc_threshold', 3.0)
        )

        self.max_accel = float(vehicle.get('max_acceleration', 3.0))
        self.max_decel = float(vehicle.get('max_deceleration', -8.0))

        self.pid_speed = PIDController(
            float(pid_speed_cfg.get('kp', 0.1)),
            float(pid_speed_cfg.get('ki', 0.0)),
            float(pid_speed_cfg.get('kd', 0.0)),
        )
        self.pid_distance = PIDController(
            float(pid_dist_cfg.get('kp', 0.1)),
            float(pid_dist_cfg.get('ki', 0.0)),
            float(pid_dist_cfg.get('kd', 0.0)),
        )

        self.speed_cap_ratio = 1.04
        self.distance_deadband = 2.0

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        ttc = None
        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        if not lead_present:
            mode = 'cruise'
        elif ttc is not None and ttc < self.emergency_ttc_threshold:
            mode = 'emergency'
        else:
            mode = 'follow'

        distance_error = None
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
        elif mode == 'follow':
            desired_distance = ego_speed * self.time_headway + self.min_distance
            distance_error = distance - desired_distance
            control_error = distance_error
            if abs(control_error) <= self.distance_deadband:
                control_error = 0.0

            accel_cmd = self.pid_distance.compute(control_error, dt)

            if distance_error < 0 and accel_cmd > 0:
                self.pid_distance.reset()
                accel_cmd = self.pid_distance.compute(control_error, dt)

            if distance_error < 0:
                accel_cmd = min(accel_cmd, 0.0)
        else:
            accel_cmd = self.max_decel

        speed_cap = self.set_speed * self.speed_cap_ratio
        if mode != 'emergency' and ego_speed >= speed_cap and accel_cmd > 0:
            accel_cmd = 0.0

        accel_cmd = _clamp(accel_cmd, self.max_decel, self.max_accel)
        return accel_cmd, mode, distance_error

from pid_controller import PIDController


def safe_following_distance(speed, time_headway, min_distance):
    return speed * time_headway + min_distance


def time_to_collision(distance, ego_speed, lead_speed):
    if distance is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None
    if distance <= 0:
        return 0.0
    return distance / relative_speed


def clamp_acceleration(accel, max_accel, max_decel):
    return max(max_decel, min(accel, max_accel))


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_cfg = config.get('acc_settings', {})
        veh_cfg = config.get('vehicle', {})
        pid_speed_cfg = config.get('pid_speed', {})
        pid_distance_cfg = config.get('pid_distance', {})

        self.set_speed = float(acc_cfg.get('set_speed', 30.0))
        self.time_headway = float(acc_cfg.get('time_headway', 1.5))
        self.min_distance = float(acc_cfg.get('min_distance', 10.0))
        self.emergency_ttc_threshold = float(acc_cfg.get('emergency_ttc_threshold', 3.0))

        self.max_accel = float(veh_cfg.get('max_acceleration', 3.0))
        self.max_decel = float(veh_cfg.get('max_deceleration', -8.0))

        self.speed_pid = PIDController(
            pid_speed_cfg.get('kp', 0.1),
            pid_speed_cfg.get('ki', 0.0),
            pid_speed_cfg.get('kd', 0.0),
        )
        self.distance_pid = PIDController(
            pid_distance_cfg.get('kp', 0.1),
            pid_distance_cfg.get('ki', 0.0),
            pid_distance_cfg.get('kd', 0.0),
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        distance_error = None

        if not lead_present:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
        else:
            ttc = time_to_collision(distance, ego_speed, lead_speed)
            desired_distance = safe_following_distance(
                ego_speed, self.time_headway, self.min_distance
            )
            distance_error = distance - desired_distance
            accel_follow = self.distance_pid.compute(distance_error, dt)
            speed_error = self.set_speed - ego_speed
            accel_speed = self.speed_pid.compute(speed_error, dt)
            accel_cmd = min(accel_follow, accel_speed)

            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_decel
            else:
                mode = 'follow'

        accel_cmd = clamp_acceleration(accel_cmd, self.max_accel, self.max_decel)
        return accel_cmd, mode, distance_error

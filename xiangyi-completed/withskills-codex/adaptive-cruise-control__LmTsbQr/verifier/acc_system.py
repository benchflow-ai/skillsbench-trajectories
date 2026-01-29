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


def determine_mode(lead_present, ttc, ttc_threshold):
    if not lead_present:
        return "cruise"
    if ttc is not None and ttc < ttc_threshold:
        return "emergency"
    return "follow"


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_settings = config.get("acc_settings", {})
        vehicle = config.get("vehicle", {})
        pid_speed_cfg = config.get("pid_speed", {})
        pid_distance_cfg = config.get("pid_distance", {})

        self.set_speed = float(acc_settings.get("set_speed", 30.0))
        self.time_headway = float(acc_settings.get("time_headway", 1.5))
        self.min_distance = float(acc_settings.get("min_distance", 10.0))
        self.emergency_ttc_threshold = float(acc_settings.get("emergency_ttc_threshold", 3.0))
        self.distance_deadband = float(acc_settings.get("distance_deadband", 2.0))
        self.follow_decel_limit = float(acc_settings.get("follow_decel_limit", -2.0))
        self.close_gain_scale = float(acc_settings.get("close_gain_scale", 0.1))
        self.emergency_brake_kp = float(acc_settings.get("emergency_brake_kp", 2.0))

        self.max_acceleration = float(vehicle.get("max_acceleration", 3.0))
        self.max_deceleration = float(vehicle.get("max_deceleration", -8.0))

        self.pid_speed = PIDController(
            pid_speed_cfg.get("kp", 0.1),
            pid_speed_cfg.get("ki", 0.0),
            pid_speed_cfg.get("kd", 0.0),
            output_min=self.max_deceleration,
            output_max=self.max_acceleration,
        )
        self.pid_distance = PIDController(
            pid_distance_cfg.get("kp", 0.1),
            pid_distance_cfg.get("ki", 0.0),
            pid_distance_cfg.get("kd", 0.0),
            output_min=self.max_deceleration,
            output_max=self.max_acceleration,
        )

        self.last_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        ttc = None
        if lead_present:
            ttc = time_to_collision(distance, ego_speed, lead_speed)

        mode = determine_mode(lead_present, ttc, self.emergency_ttc_threshold)

        if mode != self.last_mode:
            self.pid_speed.reset()
            self.pid_distance.reset()
            self.last_mode = mode

        if mode == "cruise":
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            return accel_cmd, mode, None

        desired_distance = safe_following_distance(ego_speed, self.time_headway, self.min_distance)
        distance_error = distance - desired_distance
        if abs(distance_error) <= self.distance_deadband:
            distance_error_eff = 0.0
        elif distance_error > 0:
            distance_error_eff = distance_error - self.distance_deadband
        else:
            distance_error_eff = distance_error + self.distance_deadband

        if mode == "emergency":
            if ttc is None:
                accel_cmd = self.max_deceleration
            else:
                ttc_error = self.emergency_ttc_threshold - ttc
                accel_cmd = -self.emergency_brake_kp * ttc_error
                accel_cmd = max(self.max_deceleration, accel_cmd)
        else:
            if distance_error_eff < 0:
                distance_error_eff *= self.close_gain_scale
            distance_accel = self.pid_distance.compute(distance_error_eff, dt)
            accel_cmd = distance_accel

            if distance_error_eff < 0:
                accel_cmd = max(self.follow_decel_limit, accel_cmd)

        accel_cmd = max(self.max_deceleration, min(accel_cmd, self.max_acceleration))
        return accel_cmd, mode, distance_error

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = float(config["acc_settings"]["set_speed"])
        self.time_headway = float(config["acc_settings"]["time_headway"])
        self.min_distance = float(config["acc_settings"]["min_distance"])
        self.emergency_ttc_threshold = float(config["acc_settings"]["emergency_ttc_threshold"])
        self.max_accel = float(config["vehicle"]["max_acceleration"])
        self.max_decel = float(config["vehicle"]["max_deceleration"])
        pid_speed_cfg = config.get("pid_speed", {})
        pid_dist_cfg = config.get("pid_distance", {})
        self.pid_speed = PIDController(
            pid_speed_cfg.get("kp", 0.0),
            pid_speed_cfg.get("ki", 0.0),
            pid_speed_cfg.get("kd", 0.0),
        )
        self.pid_distance = PIDController(
            pid_dist_cfg.get("kp", 0.0),
            pid_dist_cfg.get("ki", 0.0),
            pid_dist_cfg.get("kd", 0.0),
        )

    def reset(self):
        self.pid_speed.reset()
        self.pid_distance.reset()

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        if lead_speed is None or distance is None:
            return float("inf")
        closing_speed = ego_speed - lead_speed
        if closing_speed <= 0.0 or distance <= 0.0:
            return float("inf")
        return distance / closing_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)
        if lead_present and ttc < self.emergency_ttc_threshold:
            mode = "emergency"
            accel_cmd = self.max_decel
            distance_error = None
            return accel_cmd, mode, distance_error

        if not lead_present:
            mode = "cruise"
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None
        else:
            mode = "follow"
            safe_gap = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - safe_gap
            acc_distance = self.pid_distance.compute(distance_error, dt)
            target_speed = min(self.set_speed, lead_speed)
            acc_speed = self.pid_speed.compute(target_speed - ego_speed, dt)

            if distance_error < -2.0:
                accel_cmd = min(acc_distance, acc_speed)
            elif distance_error > 2.0:
                accel_cmd = max(acc_distance, acc_speed)
            else:
                accel_cmd = acc_speed

        if accel_cmd > self.max_accel:
            accel_cmd = self.max_accel
        if accel_cmd < self.max_decel:
            accel_cmd = self.max_decel
        return accel_cmd, mode, distance_error

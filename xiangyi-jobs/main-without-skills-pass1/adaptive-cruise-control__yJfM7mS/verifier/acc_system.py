"""Adaptive Cruise Control system with cruise, follow, and emergency modes."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_settings = config.get("acc_settings", {})
        vehicle = config.get("vehicle", {})
        pid_speed_cfg = config.get("pid_speed", {})
        pid_dist_cfg = config.get("pid_distance", {})

        self.set_speed = float(acc_settings.get("set_speed", 30.0))
        self.time_headway = float(acc_settings.get("time_headway", 1.5))
        self.min_distance = float(acc_settings.get("min_distance", 10.0))
        self.emergency_ttc_threshold = float(
            acc_settings.get("emergency_ttc_threshold", 3.0)
        )

        self.max_accel = float(vehicle.get("max_acceleration", 3.0))
        self.max_decel = float(vehicle.get("max_deceleration", -8.0))
        self.follow_speed_margin = 0.0

        self.speed_pid = PIDController(
            pid_speed_cfg.get("kp", 0.1),
            pid_speed_cfg.get("ki", 0.01),
            pid_speed_cfg.get("kd", 0.0),
        )
        self.distance_pid = PIDController(
            pid_dist_cfg.get("kp", 0.1),
            pid_dist_cfg.get("ki", 0.01),
            pid_dist_cfg.get("kd", 0.0),
        )
        self.prev_mode = None

    def reset(self):
        self.speed_pid.reset()
        self.distance_pid.reset()

    def _safe_distance(self, ego_speed, lead_speed=None):
        speed_ref = ego_speed if lead_speed is None else max(ego_speed, lead_speed)
        time_gap = speed_ref * self.time_headway + self.min_distance
        decel_mag = abs(self.max_decel) if self.max_decel != 0 else 1.0
        braking_gap = (ego_speed ** 2) / (2 * decel_mag) + self.min_distance
        if lead_speed is not None:
            closing_speed = max(0.0, ego_speed - lead_speed)
            closing_gap = (closing_speed ** 2) / (2 * decel_mag)
            return max(time_gap + closing_gap, braking_gap)
        return max(time_gap, braking_gap)

    def _time_to_collision(self, distance, ego_speed, lead_speed):
        if distance is None or lead_speed is None:
            return None
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def _determine_mode(self, lead_present, ttc):
        if not lead_present:
            return "cruise"
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            return "emergency"
        return "follow"

    def _clamp_accel(self, accel):
        return max(self.max_decel, min(accel, self.max_accel))

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        if lead_present:
            desired_gap = self._safe_distance(ego_speed, lead_speed)
            if lead_speed > self.set_speed and distance > desired_gap * 1.2:
                lead_present = False
        ttc = self._time_to_collision(distance, ego_speed, lead_speed)
        mode = self._determine_mode(lead_present, ttc)
        if lead_present and distance is not None and distance < self.min_distance * 0.5:
            mode = "emergency"

        if mode != self.prev_mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
            self.prev_mode = mode

        distance_error = None
        if mode == "cruise":
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            if ego_speed >= self.set_speed and accel_cmd > 0:
                accel_cmd = 0.0
        elif mode == "follow":
            desired_gap = self._safe_distance(ego_speed, lead_speed)
            distance_error = distance - desired_gap
            speed_offset = self.distance_pid.compute(distance_error, dt)
            speed_offset += distance_error / max(self.time_headway, 0.1)
            speed_offset = max(-self.set_speed, min(speed_offset, self.set_speed))
            gap_speed = max(0.0, (distance - self.min_distance) / max(self.time_headway, 0.1))
            target_speed = min(
                self.set_speed + self.follow_speed_margin,
                max(0.0, lead_speed + speed_offset),
                gap_speed,
            )
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            if ego_speed >= self.set_speed and accel_cmd > 0:
                accel_cmd = 0.0
        else:  # emergency
            desired_gap = self._safe_distance(ego_speed, lead_speed)
            distance_error = distance - desired_gap if distance is not None else None
            accel_cmd = self.max_decel

        accel_cmd = self._clamp_accel(accel_cmd)
        return accel_cmd, mode, distance_error

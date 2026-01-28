import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        vehicle_cfg = config.get("vehicle", {})
        acc_cfg = config.get("acc_settings", {})
        pid_speed_cfg = config.get("pid_speed", {})
        pid_distance_cfg = config.get("pid_distance", {})

        self.set_speed = float(acc_cfg.get("set_speed", 30.0))
        self.time_headway = float(acc_cfg.get("time_headway", 1.5))
        self.min_distance = float(acc_cfg.get("min_distance", 10.0))
        self.emergency_ttc_threshold = float(acc_cfg.get("emergency_ttc_threshold", 3.0))
        self.max_follow_speed = self.set_speed * 1.05

        self.max_accel = float(vehicle_cfg.get("max_acceleration", 3.0))
        self.max_decel = float(vehicle_cfg.get("max_deceleration", -8.0))

        self.speed_pid = PIDController(
            pid_speed_cfg.get("kp", 0.1),
            pid_speed_cfg.get("ki", 0.0),
            pid_speed_cfg.get("kd", 0.0),
        )
        self.distance_pid = PIDController(
            pid_distance_cfg.get("kp", 0.1),
            pid_distance_cfg.get("ki", 0.0),
            pid_distance_cfg.get("kd", 0.0),
        )

        self._last_mode = None

    def _clamp_accel(self, accel):
        return max(self.max_decel, min(self.max_accel, accel))

    @staticmethod
    def _is_valid(value):
        return value is not None and not math.isnan(value)

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        if not (self._is_valid(lead_speed) and self._is_valid(distance)):
            return math.inf
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 1e-6:
            return math.inf
        if distance <= 0.0:
            return 0.0
        return distance / relative_speed

    def _desired_distance(self, ego_speed, lead_speed):
        closing_speed = max(0.0, ego_speed - (lead_speed or 0.0))
        ttc_distance = closing_speed * self.emergency_ttc_threshold
        return max(self.min_distance, self.time_headway * ego_speed, ttc_distance)

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = self._is_valid(lead_speed) and self._is_valid(distance)
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        if not lead_present:
            mode = "cruise"
        elif ttc < self.emergency_ttc_threshold:
            mode = "emergency"
        else:
            mode = "follow"

        if mode != self._last_mode:
            if mode == "cruise":
                self.speed_pid.reset()
            elif mode == "follow":
                self.distance_pid.reset()
            else:
                self.speed_pid.reset()
                self.distance_pid.reset()
            self._last_mode = mode

        if mode == "cruise":
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None
        elif mode == "follow":
            desired_distance = self._desired_distance(ego_speed, lead_speed)
            distance_error = distance - desired_distance
            speed_adjust = self.distance_pid.compute(distance_error, dt)
            target_speed = min(self.max_follow_speed, (lead_speed or 0.0) + speed_adjust)
            target_speed = max(0.0, target_speed)
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
        else:
            desired_distance = self._desired_distance(ego_speed, lead_speed)
            distance_error = distance - desired_distance if lead_present else None
            accel_cmd = self.max_decel

        accel_cmd = self._clamp_accel(accel_cmd)
        return accel_cmd, mode, distance_error

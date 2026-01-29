import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_cfg = config.get("acc_settings", {})
        veh_cfg = config.get("vehicle", {})

        self.set_speed = float(acc_cfg.get("set_speed", 0.0))
        self.time_headway = float(acc_cfg.get("time_headway", 1.5))
        self.min_distance = float(acc_cfg.get("min_distance", 10.0))
        self.emergency_ttc_threshold = float(acc_cfg.get("emergency_ttc_threshold", 3.0))

        self.max_acceleration = float(veh_cfg.get("max_acceleration", 3.0))
        self.max_deceleration = float(veh_cfg.get("max_deceleration", -8.0))

        pid_speed_cfg = config.get("pid_speed", {})
        pid_distance_cfg = config.get("pid_distance", {})

        self.pid_speed = PIDController(
            pid_speed_cfg.get("kp", 0.0),
            pid_speed_cfg.get("ki", 0.0),
            pid_speed_cfg.get("kd", 0.0),
        )
        self.pid_distance = PIDController(
            pid_distance_cfg.get("kp", 0.0),
            pid_distance_cfg.get("ki", 0.0),
            pid_distance_cfg.get("kd", 0.0),
        )

        self._mode = None

    def reset(self):
        self.pid_speed.reset()
        self.pid_distance.reset()
        self._mode = None

    def _desired_gap(self, ego_speed):
        return max(self.min_distance, self.time_headway * ego_speed)

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        distance_error = None
        ttc = math.inf

        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 1e-3 and distance > 0.0:
                ttc = distance / relative_speed

        if not lead_present:
            mode = "cruise"
        elif ttc < self.emergency_ttc_threshold:
            mode = "emergency"
        else:
            mode = "follow"

        if mode != self._mode:
            if mode == "emergency":
                self.pid_speed.reset()
                self.pid_distance.reset()
            elif mode == "cruise":
                self.pid_distance.reset()
            elif mode == "follow":
                self.pid_distance.reset()
            self._mode = mode

        if mode == "emergency":
            accel_cmd = self.max_deceleration
        elif mode == "cruise":
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
        else:
            desired_gap = self._desired_gap(ego_speed)
            distance_error = desired_gap - distance
            if distance_error < 0.0:
                distance_error = 0.0

            if distance_error > 0.0:
                braking_cmd = self.pid_distance.compute(distance_error, dt)
                accel_cmd = -abs(braking_cmd)
            else:
                self.pid_distance.reset()
                target_speed = min(self.set_speed, lead_speed)
                speed_error = target_speed - ego_speed
                accel_cmd = self.pid_speed.compute(speed_error, dt)

        if accel_cmd > self.max_acceleration:
            accel_cmd = self.max_acceleration
        elif accel_cmd < self.max_deceleration:
            accel_cmd = self.max_deceleration

        return accel_cmd, mode, distance_error

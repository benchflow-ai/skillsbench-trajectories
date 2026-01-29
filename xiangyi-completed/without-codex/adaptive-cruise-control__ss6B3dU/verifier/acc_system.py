import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_settings = config["acc_settings"]
        vehicle = config["vehicle"]

        self.set_speed = float(acc_settings["set_speed"])
        self.time_headway = float(acc_settings["time_headway"])
        self.min_distance = float(acc_settings["min_distance"])
        self.emergency_ttc_threshold = float(acc_settings["emergency_ttc_threshold"])

        self.max_acceleration = float(vehicle["max_acceleration"])
        self.max_deceleration = float(vehicle["max_deceleration"])

        pid_speed_cfg = config["pid_speed"]
        pid_distance_cfg = config["pid_distance"]
        self.pid_speed = PIDController(
            pid_speed_cfg["kp"], pid_speed_cfg["ki"], pid_speed_cfg["kd"]
        )
        self.pid_distance = PIDController(
            pid_distance_cfg["kp"], pid_distance_cfg["ki"], pid_distance_cfg["kd"]
        )

        self._last_mode = None

    def _clamp_accel(self, accel_cmd):
        return max(self.max_deceleration, min(self.max_acceleration, accel_cmd))

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        distance_error = None
        ttc = math.inf

        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.0 and distance > 0.0:
                ttc = distance / relative_speed

        if not lead_present:
            mode = "cruise"
            accel_cmd = self.pid_speed.compute(self.set_speed - ego_speed, dt)
        elif ttc < self.emergency_ttc_threshold:
            mode = "emergency"
            desired_gap = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - desired_gap
            safe_speed = lead_speed + (distance / self.emergency_ttc_threshold)
            target_speed = min(ego_speed, safe_speed)
            accel_cmd = self.pid_speed.compute(target_speed - ego_speed, dt)
        else:
            mode = "follow"
            desired_gap = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - desired_gap
            speed_correction = self.pid_distance.compute(distance_error, dt)
            target_speed = lead_speed + speed_correction
            max_follow_speed = self.set_speed + 12.0
            target_speed = max(0.0, min(max_follow_speed, target_speed))
            accel_cmd = self.pid_speed.compute(target_speed - ego_speed, dt)

        if mode != self._last_mode:
            self.pid_speed.reset()
            self.pid_distance.reset()
            self._last_mode = mode

        return self._clamp_accel(accel_cmd), mode, distance_error

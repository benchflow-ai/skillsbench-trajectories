import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_settings = config["acc_settings"]
        vehicle = config["vehicle"]
        pid_speed_cfg = config["pid_speed"]
        pid_distance_cfg = config["pid_distance"]

        self.set_speed = float(acc_settings["set_speed"])
        self.time_headway = float(acc_settings["time_headway"])
        self.min_distance = float(acc_settings["min_distance"])
        self.emergency_ttc_threshold = float(acc_settings["emergency_ttc_threshold"])
        self.closing_time_headway = 0.5
        self.speed_overshoot_limit = 1.05

        self.max_acceleration = float(vehicle["max_acceleration"])
        self.max_deceleration = float(vehicle["max_deceleration"])

        self.pid_speed = PIDController(
            pid_speed_cfg["kp"], pid_speed_cfg["ki"], pid_speed_cfg["kd"]
        )
        self.pid_distance = PIDController(
            pid_distance_cfg["kp"], pid_distance_cfg["ki"], pid_distance_cfg["kd"]
        )
        self.pid_speed.integral_limit = 15.0
        self.pid_distance.integral_limit = 50.0

        self.last_ttc = None

    def reset(self):
        self.pid_speed.reset()
        self.pid_distance.reset()
        self.last_ttc = None

    def _clamp_accel(self, accel):
        return max(self.max_deceleration, min(self.max_acceleration, accel))

    def compute(self, ego_speed, lead_speed, distance, dt):
        self.last_ttc = None
        lead_present = lead_speed is not None and distance is not None

        if not lead_present:
            speed_error = self.set_speed - ego_speed
            accel = self.pid_speed.compute(speed_error, dt)
            accel = self._clamp_accel(accel)
            return accel, "cruise", None

        closing_rate = max(0.0, ego_speed - lead_speed)
        desired_gap = (
            self.min_distance
            + (self.time_headway * ego_speed)
            + (self.closing_time_headway * closing_rate)
        )
        distance_error = distance - desired_gap

        rel_speed = ego_speed - lead_speed
        if rel_speed > 0.0 and distance > 0.0:
            self.last_ttc = distance / rel_speed

        if self.last_ttc is not None and self.last_ttc < self.emergency_ttc_threshold:
            accel = self.max_deceleration
            accel = self._clamp_accel(accel)
            return accel, "emergency", distance_error

        closing_speed = self.pid_distance.compute(distance_error, dt)
        speed_cap = self.set_speed * self.speed_overshoot_limit
        target_speed = min(speed_cap, max(0.0, lead_speed + closing_speed))
        speed_cmd = self.pid_speed.compute(target_speed - ego_speed, dt)
        accel = speed_cmd
        accel = self._clamp_accel(accel)
        return accel, "follow", distance_error

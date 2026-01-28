import math

from pid_controller import PIDController


def _safe_following_distance(speed, time_headway, min_distance):
    return (speed * time_headway) + min_distance


def _time_to_collision(distance, ego_speed, lead_speed):
    if distance is None or lead_speed is None:
        return None

    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None

    if distance <= 0:
        return 0.0

    return distance / relative_speed


def _clamp_accel(accel, max_accel, max_decel):
    return max(max_decel, min(accel, max_accel))


def _is_missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_settings = config.get("acc_settings", {})
        vehicle = config.get("vehicle", {})
        pid_speed = config.get("pid_speed", {})
        pid_distance = config.get("pid_distance", {})

        self.set_speed = float(acc_settings.get("set_speed", 30.0))
        self.time_headway = float(acc_settings.get("time_headway", 1.5))
        self.min_distance = float(acc_settings.get("min_distance", 10.0))
        self.ttc_threshold = float(acc_settings.get("emergency_ttc_threshold", 3.0))

        self.max_acceleration = float(vehicle.get("max_acceleration", 3.0))
        self.max_deceleration = float(vehicle.get("max_deceleration", -8.0))

        self.speed_pid = PIDController(
            pid_speed.get("kp", 0.1),
            pid_speed.get("ki", 0.01),
            pid_speed.get("kd", 0.0),
        )
        self.distance_pid = PIDController(
            pid_distance.get("kp", 0.1),
            pid_distance.get("ki", 0.01),
            pid_distance.get("kd", 0.0),
        )
        self.speed_pid.output_min = self.max_deceleration
        self.speed_pid.output_max = self.max_acceleration
        self.distance_pid.output_min = self.max_deceleration
        self.distance_pid.output_max = self.max_acceleration
        self.speed_buffer = 10.0
        self.emergency_brake_gain = 0.2
        self.emergency_gap_gain = 0.5
        self.relative_speed_gain = 0.7

        self.last_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = not _is_missing(lead_speed) and not _is_missing(distance)
        ttc = _time_to_collision(distance, ego_speed, lead_speed) if lead_present else None

        if not lead_present:
            mode = "cruise"
        elif distance is not None and distance <= self.min_distance:
            mode = "emergency"
        elif ttc is not None and ttc < self.ttc_threshold:
            mode = "emergency"
        else:
            mode = "follow"

        if mode != self.last_mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
            self.last_mode = mode

        distance_error = None
        if mode == "cruise":
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
        elif mode == "emergency":
            distance_error = distance - _safe_following_distance(
                ego_speed, self.time_headway, self.min_distance
            )
            relative_speed = ego_speed - lead_speed
            accel_cmd = -self.emergency_brake_gain * max(0.0, relative_speed)
            if distance is not None and distance <= self.min_distance:
                gap_error = self.min_distance - distance
                accel_cmd -= self.emergency_gap_gain * max(0.0, gap_error)
        else:
            distance_error = distance - _safe_following_distance(
                ego_speed, self.time_headway, self.min_distance
            )
            relative_speed = lead_speed - ego_speed
            speed_offset = self.distance_pid.compute(distance_error, dt)
            speed_offset += self.relative_speed_gain * relative_speed
            target_speed = lead_speed + speed_offset
            max_speed = self.set_speed + self.speed_buffer
            target_speed = min(target_speed, max_speed)
            target_speed = max(0.0, target_speed)
            speed_error = target_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        accel_cmd = _clamp_accel(accel_cmd, self.max_acceleration, self.max_deceleration)
        return accel_cmd, mode, distance_error

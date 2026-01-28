import math

from pid_controller import PIDController


def safe_following_distance(
    speed, time_headway, min_distance, relative_speed, max_decel, braking_factor=0.0
):
    braking_distance = 0.0
    if max_decel < 0 and relative_speed > 0:
        braking_distance = (
            braking_factor * (relative_speed ** 2) / (2 * abs(max_decel))
        )
    return max(min_distance, speed * time_headway + min_distance + braking_distance)


def time_to_collision(distance, ego_speed, lead_speed):
    if distance is None:
        return None
    relative_speed = ego_speed - lead_speed
    if relative_speed <= 0:
        return None
    if distance <= 0:
        return 0.0
    return distance / relative_speed


def _is_valid_number(value):
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    return True


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.set_speed = config["acc_settings"]["set_speed"]
        self.time_headway = config["acc_settings"]["time_headway"]
        self.min_distance = config["acc_settings"]["min_distance"]
        self.emergency_ttc_threshold = config["acc_settings"]["emergency_ttc_threshold"]
        self.max_acceleration = config["vehicle"]["max_acceleration"]
        self.max_deceleration = config["vehicle"]["max_deceleration"]

        speed_gains = config["pid_speed"]
        distance_gains = config["pid_distance"]
        self.speed_pid = PIDController(
            speed_gains["kp"], speed_gains["ki"], speed_gains["kd"]
        )
        self.distance_pid = PIDController(
            distance_gains["kp"], distance_gains["ki"], distance_gains["kd"]
        )
        self.speed_pid.output_min = self.max_deceleration
        self.speed_pid.output_max = self.max_acceleration
        self.distance_pid.output_min = -self.set_speed
        self.distance_pid.output_max = self.set_speed

        self._last_mode = None
        self.follow_speed_gain = 2.5

    def _clamp_acceleration(self, accel):
        return max(self.max_deceleration, min(accel, self.max_acceleration))

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = _is_valid_number(lead_speed) and _is_valid_number(distance)
        if not lead_present:
            mode = "cruise"
            ttc = None
        else:
            ttc = time_to_collision(distance, ego_speed, lead_speed)
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = "emergency"
            else:
                mode = "follow"

        if mode != self._last_mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
            self._last_mode = mode

        distance_error = None
        if mode == "cruise":
            error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(error, dt)
            if error > 5.0:
                accel_cmd = self.max_acceleration
            if error < -5.0:
                accel_cmd = self.max_deceleration
            if ego_speed >= self.set_speed and accel_cmd > 0:
                accel_cmd = 0.0
        elif mode == "follow":
            relative_speed = max(0.0, ego_speed - lead_speed)
            safe_distance = safe_following_distance(
                ego_speed,
                self.time_headway,
                self.min_distance,
                relative_speed,
                self.max_deceleration,
            )
            distance_error = distance - safe_distance
            relative_speed = lead_speed - ego_speed
            accel_cmd = self.distance_pid.compute(distance_error, dt)
            accel_cmd += self.follow_speed_gain * relative_speed
            if ego_speed >= self.set_speed * 1.3 and accel_cmd > 0:
                accel_cmd = 0.0
        else:  # emergency
            relative_speed = max(0.0, ego_speed - lead_speed)
            safe_distance = safe_following_distance(
                ego_speed,
                self.time_headway,
                self.min_distance,
                relative_speed,
                self.max_deceleration,
            )
            distance_error = distance - safe_distance
            if ttc is None or ttc <= 0:
                accel_cmd = self.max_deceleration
            else:
                required_decel = -(ego_speed - lead_speed) / ttc
                accel_cmd = max(self.max_deceleration, required_decel)

        return self._clamp_acceleration(accel_cmd), mode, distance_error

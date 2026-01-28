import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        vehicle_cfg = config.get('vehicle', {})
        acc_cfg = config.get('acc_settings', {})
        pid_speed_cfg = config.get('pid_speed', {})
        pid_distance_cfg = config.get('pid_distance', {})

        self.set_speed = float(acc_cfg.get('set_speed', 0.0))
        self.time_headway = float(acc_cfg.get('time_headway', 1.5))
        self.min_distance = float(acc_cfg.get('min_distance', 10.0))
        self.emergency_ttc_threshold = float(acc_cfg.get('emergency_ttc_threshold', 3.0))

        self.max_accel = float(vehicle_cfg.get('max_acceleration', 3.0))
        self.max_decel = float(vehicle_cfg.get('max_deceleration', -8.0))

        self.speed_pid = PIDController(
            pid_speed_cfg.get('kp', 0.0),
            pid_speed_cfg.get('ki', 0.0),
            pid_speed_cfg.get('kd', 0.0),
        )
        self.distance_pid = PIDController(
            pid_distance_cfg.get('kp', 0.0),
            pid_distance_cfg.get('ki', 0.0),
            pid_distance_cfg.get('kd', 0.0),
        )
        self._last_mode = None

    def _safe_distance(self, speed):
        return self.min_distance + self.time_headway * speed

    def _time_to_collision(self, distance, ego_speed, lead_speed):
        if distance is None or lead_speed is None:
            return None
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return None
        return distance / relative_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        ttc = None
        if lead_present:
            ttc = self._time_to_collision(distance, ego_speed, lead_speed)

        if not lead_present:
            mode = 'cruise'
            distance_error = None
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
        elif ttc is not None and ttc < self.emergency_ttc_threshold:
            mode = 'emergency'
            desired_distance = self._safe_distance(ego_speed)
            distance_error = distance - desired_distance
            accel_cmd = self.max_decel
        else:
            mode = 'follow'
            desired_distance = self._safe_distance(ego_speed)
            distance_error = distance - desired_distance
            accel_cmd = self.distance_pid.compute(distance_error, dt)

        if self._last_mode is None:
            self._last_mode = mode
        elif self._last_mode != mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
            self._last_mode = mode

        accel_cmd = max(self.max_decel, min(accel_cmd, self.max_accel))
        return accel_cmd, mode, distance_error

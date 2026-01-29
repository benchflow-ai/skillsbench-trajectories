import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        acc_settings = config.get('acc_settings', {})
        vehicle = config.get('vehicle', {})
        pid_speed_cfg = config.get('pid_speed', {})
        pid_dist_cfg = config.get('pid_distance', {})

        self.set_speed = float(acc_settings.get('set_speed', 30.0))
        self.time_headway = float(acc_settings.get('time_headway', 1.5))
        self.min_distance = float(acc_settings.get('min_distance', 10.0))
        self.emergency_ttc_threshold = float(acc_settings.get('emergency_ttc_threshold', 3.0))

        self.max_acceleration = float(vehicle.get('max_acceleration', 3.0))
        self.max_deceleration = float(vehicle.get('max_deceleration', -8.0))

        self.speed_pid = PIDController(
            pid_speed_cfg.get('kp', 0.1),
            pid_speed_cfg.get('ki', 0.0),
            pid_speed_cfg.get('kd', 0.0),
        )
        self.distance_pid = PIDController(
            pid_dist_cfg.get('kp', 0.1),
            pid_dist_cfg.get('ki', 0.0),
            pid_dist_cfg.get('kd', 0.0),
        )

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        if lead_speed is None or distance is None:
            return math.inf
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0 or distance <= 0:
            return math.inf
        return distance / relative_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
            return accel_cmd, 'cruise', None

        desired_gap = self.min_distance + self.time_headway * ego_speed
        distance_error = distance - desired_gap
        ttc = self._compute_ttc(ego_speed, lead_speed, distance)

        if ttc < self.emergency_ttc_threshold:
            accel_cmd = self.max_deceleration
            return accel_cmd, 'emergency', distance_error

        # Follow mode: distance PID sets a speed offset relative to lead, speed PID tracks it.
        speed_offset = self.distance_pid.compute(distance_error, dt)
        speed_offset = max(-10.0, min(10.0, speed_offset))
        speed_margin = 5.0
        target_speed = min(self.set_speed + speed_margin, lead_speed + speed_offset)
        speed_error = target_speed - ego_speed
        accel_cmd = self.speed_pid.compute(speed_error, dt)
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
        return accel_cmd, 'follow', distance_error

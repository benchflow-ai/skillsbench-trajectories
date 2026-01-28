import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        vehicle = config.get('vehicle', {})
        acc_settings = config.get('acc_settings', {})
        pid_speed_cfg = config.get('pid_speed', {})
        pid_dist_cfg = config.get('pid_distance', {})

        self.set_speed = float(acc_settings.get('set_speed', 0.0))
        self.time_headway = float(acc_settings.get('time_headway', 1.5))
        self.min_distance = float(acc_settings.get('min_distance', 10.0))
        self.emergency_ttc_threshold = float(
            acc_settings.get('emergency_ttc_threshold', 3.0)
        )
        self.catch_up_margin = float(acc_settings.get('catch_up_margin', 5.0))

        self.max_acceleration = float(vehicle.get('max_acceleration', 3.0))
        self.max_deceleration = float(vehicle.get('max_deceleration', -8.0))

        self.speed_pid = PIDController(
            pid_speed_cfg.get('kp', 0.0),
            pid_speed_cfg.get('ki', 0.0),
            pid_speed_cfg.get('kd', 0.0),
            integrator_limit=pid_speed_cfg.get('integrator_limit', None),
        )
        self.distance_pid = PIDController(
            pid_dist_cfg.get('kp', 0.0),
            pid_dist_cfg.get('ki', 0.0),
            pid_dist_cfg.get('kd', 0.0),
            integrator_limit=pid_dist_cfg.get('integrator_limit', None),
        )

    @staticmethod
    def _compute_ttc(distance, ego_speed, lead_speed):
        if distance is None:
            return None
        closing_speed = ego_speed - lead_speed
        if closing_speed <= 1e-6:
            return math.inf
        return max(0.0, distance / closing_speed)

    def compute(self, ego_speed, lead_speed, distance, dt):
        mode = 'cruise'
        distance_error = None

        if lead_speed is None or distance is None:
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
        else:
            ttc = self._compute_ttc(distance, ego_speed, lead_speed)
            if ttc is not None and ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                acceleration_cmd = self.max_deceleration
            else:
                mode = 'follow'
                desired_distance = max(self.min_distance, self.time_headway * ego_speed)
                distance_error = distance - desired_distance
                # When too close, prioritize distance controller for braking
                if distance_error < 0.0:
                    speed_error = self.set_speed - ego_speed
                    speed_cmd = self.speed_pid.compute(speed_error, dt)
                    dist_cmd = self.distance_pid.compute(distance_error, dt)
                    acceleration_cmd = min(speed_cmd, dist_cmd)
                else:
                    # When far, target a follow speed that closes the gap without passing the lead
                    follow_target = lead_speed + (distance_error / max(self.time_headway, 1e-3))
                    max_follow_speed = max(self.set_speed, lead_speed) + self.catch_up_margin
                    if follow_target > max_follow_speed:
                        follow_target = max_follow_speed
                    if follow_target < 0.0:
                        follow_target = 0.0
                    speed_error = follow_target - ego_speed
                    acceleration_cmd = self.speed_pid.compute(speed_error, dt)

        if acceleration_cmd > self.max_acceleration:
            acceleration_cmd = self.max_acceleration
        elif acceleration_cmd < self.max_deceleration:
            acceleration_cmd = self.max_deceleration

        return acceleration_cmd, mode, distance_error

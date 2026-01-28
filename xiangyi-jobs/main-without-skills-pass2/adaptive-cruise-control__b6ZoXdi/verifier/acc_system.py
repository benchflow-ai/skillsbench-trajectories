import math
from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_cfg = config.get('acc_settings', {})
        veh_cfg = config.get('vehicle', {})

        self.set_speed = acc_cfg.get('set_speed', 30.0)
        self.time_headway = acc_cfg.get('time_headway', 1.5)
        self.min_distance = acc_cfg.get('min_distance', 10.0)
        self.emergency_ttc_threshold = acc_cfg.get('emergency_ttc_threshold', 3.0)

        self.max_acceleration = veh_cfg.get('max_acceleration', 3.0)
        self.max_deceleration = veh_cfg.get('max_deceleration', -8.0)

        pid_speed_cfg = config.get('pid_speed', {})
        pid_dist_cfg = config.get('pid_distance', {})
        self.speed_pid = PIDController(pid_speed_cfg.get('kp', 0.0),
                                       pid_speed_cfg.get('ki', 0.0),
                                       pid_speed_cfg.get('kd', 0.0))
        self.distance_pid = PIDController(pid_dist_cfg.get('kp', 0.0),
                                          pid_dist_cfg.get('ki', 0.0),
                                          pid_dist_cfg.get('kd', 0.0))

    def _clamp_accel(self, accel):
        if accel > self.max_acceleration:
            return self.max_acceleration
        if accel < self.max_deceleration:
            return self.max_deceleration
        return accel

    def compute(self, ego_speed, lead_speed, distance, dt):
        distance_error = None

        lead_missing = (lead_speed is None or distance is None or
                        (isinstance(lead_speed, float) and math.isnan(lead_speed)) or
                        (isinstance(distance, float) and math.isnan(distance)))

        if lead_missing:
            # Cruise mode
            self.distance_pid.reset()
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = self._clamp_accel(accel_cmd)
            return accel_cmd, mode, distance_error

        # Lead vehicle present
        desired_distance = self.min_distance + self.time_headway * ego_speed
        distance_error = distance - desired_distance

        relative_speed = ego_speed - lead_speed
        ttc = float('inf')
        if relative_speed > 0 and distance > 0:
            ttc = distance / relative_speed

        if ttc < self.emergency_ttc_threshold:
            mode = 'emergency'
            self.speed_pid.reset()
            self.distance_pid.reset()
            accel_cmd = self.max_deceleration
        else:
            mode = 'follow'
            # outer loop: spacing error -> speed correction
            delta_v = self.distance_pid.compute(distance_error, dt)
            speed_target = lead_speed + delta_v
            if speed_target > self.set_speed:
                speed_target = self.set_speed
            if speed_target < 0.0:
                speed_target = 0.0
            speed_error = speed_target - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)

        accel_cmd = self._clamp_accel(accel_cmd)
        return accel_cmd, mode, distance_error

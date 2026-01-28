import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = float(config['acc_settings']['set_speed'])
        self.time_headway = float(config['acc_settings']['time_headway'])
        self.min_distance = float(config['acc_settings']['min_distance'])
        self.emergency_ttc_threshold = float(
            config['acc_settings']['emergency_ttc_threshold']
        )
        self.max_accel = float(config['vehicle']['max_acceleration'])
        self.max_decel = float(config['vehicle']['max_deceleration'])

        self.speed_pid = PIDController(**config['pid_speed'])
        self.distance_pid = PIDController(**config['pid_distance'])
        self.last_mode = None

    def _is_valid(self, value):
        return value is not None and not (isinstance(value, float) and math.isnan(value))

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = self._is_valid(lead_speed) and self._is_valid(distance)
        ttc = None

        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed if distance > 0 else 0.0
            else:
                ttc = math.inf

        if lead_present and ttc is not None and ttc < self.emergency_ttc_threshold:
            mode = 'emergency'
        elif lead_present:
            mode = 'follow'
        else:
            mode = 'cruise'

        if self.last_mode != mode:
            self.speed_pid.reset()
            self.distance_pid.reset()
        self.last_mode = mode

        distance_error = None

        if mode == 'emergency':
            desired_gap = self.min_distance + self.time_headway * ego_speed
            distance_error = desired_gap - distance if lead_present else None
            acceleration_cmd = self.max_decel
        elif mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
        else:
            desired_gap = self.min_distance + self.time_headway * ego_speed
            distance_error = desired_gap - distance
            if distance_error > 0:
                acceleration_cmd = -self.distance_pid.compute(distance_error, dt)
            else:
                distance_error = 0.0
                speed_error = self.set_speed - ego_speed
                acceleration_cmd = self.speed_pid.compute(speed_error, dt)

        acceleration_cmd = max(self.max_decel, min(self.max_accel, acceleration_cmd))
        return acceleration_cmd, mode, distance_error, ttc

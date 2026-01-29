import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = float(config['acc_settings']['set_speed'])
        self.time_headway = float(config['acc_settings']['time_headway'])
        self.min_distance = float(config['acc_settings']['min_distance'])
        self.ttc_threshold = float(config['acc_settings']['emergency_ttc_threshold'])

        self.max_accel = float(config['vehicle']['max_acceleration'])
        self.max_decel = float(config['vehicle']['max_deceleration'])
        self.rel_speed_gain = 1.0
        self.extra_headway = 0.6
        self.lead_detection_range = 55.0

        pid_speed = config['pid_speed']
        pid_distance = config['pid_distance']
        self.speed_controller = PIDController(
            pid_speed['kp'], pid_speed['ki'], pid_speed['kd']
        )
        self.distance_controller = PIDController(
            pid_distance['kp'], pid_distance['ki'], pid_distance['kd']
        )

        self._last_mode = None

    def _desired_distance(self, ego_speed, lead_speed=None):
        base = ego_speed * self.time_headway + self.min_distance
        if lead_speed is None:
            return max(self.min_distance, base)
        extra = max(ego_speed, lead_speed) * self.extra_headway
        return max(self.min_distance, base + extra)

    def _time_to_collision(self, distance, ego_speed, lead_speed):
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0:
            return None
        if distance <= 0:
            return 0.0
        return distance / relative_speed

    def _clamp_acceleration(self, accel):
        return max(self.max_decel, min(accel, self.max_accel))

    def _update_mode(self, mode):
        if mode == self._last_mode:
            return
        self.speed_controller.reset()
        self.distance_controller.reset()
        self._last_mode = mode

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = (
            lead_speed is not None
            and distance is not None
            and not math.isnan(lead_speed)
            and not math.isnan(distance)
        )
        if lead_present and distance > self.lead_detection_range:
            lead_present = False

        ttc = None
        if lead_present:
            ttc = self._time_to_collision(distance, ego_speed, lead_speed)

        if not lead_present:
            mode = 'cruise'
        elif distance < self.min_distance or (ttc is not None and ttc < self.ttc_threshold):
            mode = 'emergency'
        else:
            mode = 'follow'

        self._update_mode(mode)

        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
            distance_error = None
        elif mode == 'follow':
            desired_distance = self._desired_distance(ego_speed, lead_speed)
            distance_error = distance - desired_distance
            rel_speed = lead_speed - ego_speed
            accel_cmd = self.distance_controller.compute(distance_error, dt) + self.rel_speed_gain * rel_speed
        else:
            desired_distance = self._desired_distance(ego_speed, lead_speed) if lead_present else None
            distance_error = distance - desired_distance if desired_distance is not None else None
            if distance_error is None:
                accel_cmd = self.max_decel
            else:
                rel_speed = lead_speed - ego_speed if lead_present else 0.0
                accel_cmd = self.distance_controller.compute(distance_error, dt) + self.rel_speed_gain * rel_speed

        accel_cmd = self._clamp_acceleration(accel_cmd)
        return accel_cmd, mode, distance_error
